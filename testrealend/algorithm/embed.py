import logging
import os
import random
from decimal import Decimal
import numpy as np
from PIL import Image
from algorithm.get_coor import get_coor_nested, get_coor_array
import zipfile
from algorithm.to_geodataframe import to_geodataframe


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
    # print(x, embed_x, xl)
    # print(w,(embed_x-xl)// ((xr - xl) / 2 ** n))
    # print(coor_l,x, w, embed_x)
    # print(w)
    return np.vstack([embed_x, embed_y])


def coor_process(coor, argument, dis):
    """
    对坐标进行处理
    :param coor: 需要处理的坐标
    :return: 嵌入水印的坐标
    """
    n, R, W = argument.values()

    random.seed(dis)

    index = random.randint(0, len(W) - 1)  # 抵抗删点、平移、缩放 不抵抗旋转
    # print(dis,index)
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
            dis = abs(coor[1] - coor_group[:, i + 1][1])
            # print(coor[1] ,coor_group[:, i + 1][1],dis)
            embed_coor = coor_process(coor, argument, dis)
            # print(embed_coor)
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
        # print(coor_nested)
        # print(coor_nested[:, feature_index])
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


def embed(shpfile_path, watermark_path, output_filename):
    import geopandas as gpd
    # -------------------------预定义--------------------------------
    n = 4  # 嵌入强度
    tau = 10 ** (-6)  # 精度容差
    R = Decimal('1e-7')

    # -------------------------数据读取--------------------------------
    original_shpfile = gpd.read_file(shpfile_path)
    coor_nested, feature_type = get_coor_nested(original_shpfile)
    watermark = np.array(Image.open(watermark_path)).astype(int)

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
    print(vr)

    # -------------------------数据输出--------------------------------
    output_dir = os.path.join(os.getcwd(), 'embed')
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

    print("ZIP文件创建完成，已保存为", zip_file_path)

    # -------------------------删除原始文件--------------------------------
    try:
        for ext in shapefile_extensions:
            filepath = shapefile_path.replace('.shp', ext)
            if os.path.exists(filepath):
                os.remove(filepath)
        print("原始文件已删除。")
    except Exception as e:
        print(f"删除文件时出错: {e}")

    return zip_file_path, vr


if __name__ == "__main__":
    shpfile_path = r"E:\矢量数据\数据\Road\Road.shp"
    watermark_path = "../temp_qrcode.png"
    output_filename = "../embed/11WuJiang.shp"
    embed(shpfile_path, watermark_path, output_filename)
