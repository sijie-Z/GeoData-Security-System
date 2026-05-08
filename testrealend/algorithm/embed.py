import logging
import os
import random
import hashlib
from decimal import Decimal
import numpy as np
from PIL import Image
from algorithm.get_coor import get_coor_nested, get_coor_array
from algorithm.quality_metrics import capacity_report
import zipfile
from algorithm.to_geodataframe import to_geodataframe


def _compute_seed(c1, c2):
    """Compute a deterministic seed from two coordinate pairs using both x and y.
    Uses MD5 hash to avoid seed=0 when coordinates are identical in one dimension."""
    raw = f"{float(c1[0]):.15f},{float(c1[1]):.15f},{float(c2[0]):.15f},{float(c2[1]):.15f}"
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


def watermark_embed(coor, coor_l, w, n, R):
    """
    对坐标嵌入水印
    :param coor: 变换后的坐标
    :param w: 水印
    :param coor_l: 区域左下角顶点的坐标
    :return:返回嵌入水印的坐标
    """
    x, y = coor
    xl, yl = coor_l
    k = (x - xl) / 2 ** n
    # embed_x = xl + w * ((xr - xl) / 2 ** n) + k
    embed_x = xl + w * (R / 2 ** n) + k
    embed_y = y
    return np.vstack([embed_x, embed_y])


def coor_process(coor, argument, seed):
    """
    对坐标进行处理
    :param coor: 需要处理的坐标
    :param seed: 确定性种子
    :return: 嵌入水印的坐标
    """
    n, R, W = argument.values()

    random.seed(seed)

    index = random.randint(0, len(W) - 1)  # 抵抗删点、平移、缩放 不抵抗旋转
    w = int(''.join(map(str, W[index])), 2)

    coor = np.array([Decimal(str(x)) for x in np.nditer(coor)])
    coor_l = coor // R * R
    embed_coor = watermark_embed(coor, coor_l, w, n, R)
    return embed_coor


def coor_group_process(coor_group, argument):
    """
    对坐标组进行处理
    :param coor_group:需要处理的坐标组
    :return: 返回嵌入水印的坐标组
    """
    embed_coor_group = np.array([[], []])
    for i in range(coor_group.shape[1]):
        coor = coor_group[:, i]
        if i == coor_group.shape[1] - 1:
            embed_coor = coor[:, np.newaxis]
        else:
            next_coor = coor_group[:, i + 1]
            seed = _compute_seed(coor, next_coor)
            embed_coor = coor_process(coor, argument, seed)
        embed_coor_group = np.concatenate((embed_coor_group, embed_coor), axis=1)
    return embed_coor_group


def traversal_nested_coor_group(coor_nested, feature_type, argument):
    """
    对于多线、多面等情况，执行此函数
    :param coor_nested: 所有要素组成的嵌套坐标数组
    :param feature_type: 要素的类型
    :return: 返回该要素更新后的嵌套坐标组
    """
    processed_x_nested = []
    processed_y_nested = []
    # 遍历要素中的每个坐标组
    for feature_index in range(coor_nested.shape[1]):
        coor_group = np.vstack(coor_nested[:, feature_index])
        # 对坐标进行平移
        processed_coor_group = coor_group_process(coor_group, argument)
        # 如果要素为多面，则需要满足首位顶点的坐标相同
        if (feature_type == 'MultiPolygon'
                and np.size(processed_coor_group) not in [0, 2]
                and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
            processed_coor_group[:, -1] = processed_coor_group[:, 0]
        processed_x_nested.append(processed_coor_group[0, :])
        processed_y_nested.append(processed_coor_group[1, :])
    return np.array([processed_x_nested, processed_y_nested], dtype=object)


def traversal_coor_group(coor_nested, shp_type, processed_shpfile, argument):
    """
    对所有要素进行遍历
    :param coor_nested: 所有要素组成的嵌套坐标数组
    :param shp_type: 每个要素类型组成的数组
    :param processed_shpfile: 处理后的shp文件
    :return: processed_shpfile
    """
    # 遍历每个几何要素
    for feature_index in range(coor_nested.shape[1]):
        coor_group = np.vstack(coor_nested[:, feature_index])
        feature_type = shp_type[feature_index]
        # 判断是否是多线、多面等的情况
        if isinstance(coor_group[0, 0], np.ndarray):
            processed_coor_group = traversal_nested_coor_group(coor_group, feature_type, argument)
        else:
            processed_coor_group = coor_group_process(coor_group, argument)
            # 如果要素为面，则需要满足首尾顶点的坐标相同
            if (feature_type == 'Polygon'
                    and np.size(processed_coor_group) not in [0, 2]
                    and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
                processed_coor_group[:, -1] = processed_coor_group[:, 0]
        # 将改变的要素坐标组更新到geodataframe
        processed_shpfile = to_geodataframe(processed_shpfile, feature_index, processed_coor_group,
                                            shp_type[feature_index])
    return processed_shpfile


def embed(shp_path, qr_image_path, n=4, R=Decimal('1e-7'), output_dir=None):
    import geopandas as gpd
    if output_dir is None:
        from flask import current_app
        output_dir = current_app.config['WATERMARK_FOLDER']
    output_filename = f"watermarked_{os.path.basename(shp_path)}"

    # -------------------------数据读取--------------------------------
    original_shpfile = gpd.read_file(shp_path)
    coor_nested, feature_type = get_coor_nested(original_shpfile)
    watermark = np.array(Image.open(qr_image_path)).astype(int)

    # -------------------------容量检查--------------------------------
    watermark_proc = watermark.copy()
    replace_matrix_check = np.full((8, 8), -1)
    watermark_proc[:8, :8] = watermark_proc[:8, -8:] = watermark_proc[-8:, :8] = replace_matrix_check
    watermark_proc = watermark_proc.flatten()
    watermark_proc = list(filter(lambda x: x != -1, watermark_proc))
    n_bits_needed = len(watermark_proc)
    total_vertices = sum(
        coor_nested[:, i][0].size if not isinstance(coor_nested[:, i][0], (list, np.ndarray)) or
        (isinstance(coor_nested[:, i][0], np.ndarray) and coor_nested[:, i][0].ndim == 1)
        else sum(arr.size for arr in coor_nested[:, i][0])
        for i in range(coor_nested.shape[1])
    )
    cap_report = capacity_report(total_vertices, n_bits_needed, n)
    if not cap_report['sufficient']:
        raise ValueError(
            f"Insufficient embedding capacity: need {cap_report['needed_chunks']} chunks "
            f"but only {cap_report['available_chunks']} available "
            f"({cap_report['total_vertices']} vertices, utilization would be {cap_report['utilization_percent']}%)"
        )
    logging.info('Capacity report: %s', cap_report)

    # -------------------------数据预处理--------------------------------
    replace_matrix = np.full((8, 8), -1)
    watermark[:8, :8] = watermark[:8, -8:] = watermark[-8:, :8] = replace_matrix
    watermark = watermark.flatten()
    watermark = list(filter(lambda x: x != -1, watermark))
    watermark += [0] * ((n - len(watermark) % n) % n)
    W = np.array_split(watermark, len(watermark) // n)
    argument = {'n': n, 'R': R, 'W': W}

    # -------------------------水印嵌入--------------------------------
    watermarked_shpfile = original_shpfile.copy()
    watermarked_shpfile = traversal_coor_group(coor_nested, feature_type, watermarked_shpfile, argument)

    coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    coor_array = get_coor_array(coor_nested, feature_type)
    vr = np.mean(coor_array, axis=1)
    vr = [float(format(coor, '.15f')) for coor in vr]
    logging.info('vr: %s', vr)

    # -------------------------数据输出--------------------------------
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create Shapefile
    shapefile_path = os.path.join(output_dir, output_filename)
    watermarked_shpfile.to_file(shapefile_path)

    # 定义 Shapefile 相关的文件扩展名
    shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg']

    # 创建一个新的 ZIP 文件，并将 Shapefile 的各个部分添加到 ZIP 中
    zip_filename = f"{output_filename.replace('.shp', '.zip')}"
    zip_file_path = os.path.join(output_dir, zip_filename)

    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for ext in shapefile_extensions:
            filepath = shapefile_path.replace('.shp', ext)
            if os.path.exists(filepath):
                zipf.write(filepath, os.path.basename(filepath))

    logging.info("ZIP文件创建完成，已保存为 %s", zip_file_path)

    # -------------------------删除原始文件--------------------------------
    try:
        for ext in shapefile_extensions:
            filepath = shapefile_path.replace('.shp', ext)
            if os.path.exists(filepath):
                os.remove(filepath)
        logging.info("原始文件已删除。")
    except Exception as e:
        logging.error("删除文件时出错: %s", e)

    return {
        'zip_path': zip_file_path,
        'vr': vr,
        'capacity_report': cap_report
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Embed watermark into shapefile')
    parser.add_argument('shp_path', help='Input shapefile path')
    parser.add_argument('qr_image_path', help='QR code image path')
    parser.add_argument('--output-dir', default=os.path.join(os.getcwd(), 'embed'))
    args = parser.parse_args()
    result = embed(args.shp_path, args.qr_image_path, output_dir=args.output_dir)
    logging.info('Embed result: %s', result)
