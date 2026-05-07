import math
import os
import random
import sys
from collections import Counter
from decimal import Decimal

import numpy as np
from PIL import Image
from flask import current_app

from algorithm.get_coor import get_coor_nested, get_coor_array
from algorithm.to_geodataframe import to_geodataframe
from algorithm.NC import NC, image_to_array


def watermark_extract(coor, coor_l, R, n):
    """
    对坐标嵌入水印
    :param coor: 变换后的坐标
    :param coor_l: 区域左下角顶点的坐标
    :return:返回嵌入水印的坐标
    """
    x, y = coor
    xl, yl = coor_l
    w = (x - xl) // (R / 2 ** n)
    original_x = xl + 2 ** n * (x - xl) - w * R
    original_y = y
    return np.vstack([original_x, original_y]), int(w)


def coor_process(coor, W, dis, argument):
    """
    对坐标进行处理
    :param coor: 需要处理的坐标
    :return: 嵌入水印的坐标
    """
    n, R, side_length, ratio = argument.values()
    random.seed(dis)

    index = random.randint(0, len(W) - 1)
    coor = np.array([Decimal(str(x)) for x in coor])
    coor_l = coor // R * R
    original_coor, w = watermark_extract(coor, coor_l, R, n)
    W[index].append(w)
    return original_coor, W


def coor_group_process(coor_group, W, argument):
    """
    对坐标组进行处理
    :param coor_group:需要处理的坐标组
    :return: 返回嵌入水印的坐标组
    """
    n, R, side_length, ratio = argument.values()
    coor_group = coor_group * ratio
    original_coor_group = np.array([[], []])
    for i in range(coor_group.shape[1]):
        coor = coor_group[:, i]
        if i == coor_group.shape[1] - 1:
            original_coor = coor[:, np.newaxis]
        else:
            dis = abs(coor[1] - coor_group[:, i + 1][1])
            original_coor, W = coor_process(coor, W, dis, argument)
        original_coor_group = np.concatenate((original_coor_group, original_coor), axis=1)
    return original_coor_group, W


def traversal_nested_coor_group(coor_nested, feature_type, W, argument):
    """
    对于多线、多面等情况，执行此函数
    :param coor_nested: 所有要素组成的嵌套坐标数组
    :param feature_type: 要素的类型
    :return: 返回该要素更新后的嵌套坐标组
    """
    processed_x_nested = []
    processed_y_nested = []
    for feature_index in range(coor_nested.shape[1]):
        coor_group = np.vstack(coor_nested[:, feature_index])
        processed_coor_group, W = coor_group_process(coor_group, W, argument)
        if (feature_type == 'MultiPolygon'
                and np.size(processed_coor_group) not in [0, 2]
                and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
            processed_coor_group[:, -1] = processed_coor_group[:, 0]
        processed_x_nested.append(processed_coor_group[0, :])
        processed_y_nested.append(processed_coor_group[1, :])
    return np.array([processed_x_nested, processed_y_nested], dtype=object), W


def traversal_coor_group(coor_nested, shp_type, processed_shpfile, l, argument):
    """
    对所有要素进行遍历
    :param coor_nested: 所有要素组成的嵌套坐标数组
    :param shp_type: 每个要素类型组成的数组
    :param processed_shpfile: 处理后的shp文件
    :return: processed_shpfile
    """
    W = [[] for _ in range(l)]

    for feature_index in range(coor_nested.shape[1]):
        coor_group = np.vstack(coor_nested[:, feature_index])
        if isinstance(coor_nested[:, feature_index][0], list):
            continue
        feature_type = shp_type[feature_index]
        if isinstance(coor_group[0, 0], np.ndarray):
            processed_coor_group, W = traversal_nested_coor_group(coor_group, feature_type, W, argument)
        else:
            processed_coor_group, W = coor_group_process(coor_group, W, argument)
            if (feature_type == 'Polygon'
                    and np.size(processed_coor_group) not in [0, 2]
                    and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
                processed_coor_group[:, -1] = processed_coor_group[:, 0]
        processed_shpfile = to_geodataframe(processed_shpfile, feature_index, processed_coor_group,
                                             shp_type[feature_index])
    return processed_shpfile, W


def calculate_watermark_and_nc(watermarked_shpfile, l, argument):
    watermarked_coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    n, R, side_length, ratio = argument.values()

    original_shpfile = watermarked_shpfile.copy()
    original_shpfile, W = traversal_coor_group(watermarked_coor_nested, feature_type, original_shpfile, l,
                                               argument)

    empty_array_flag = False
    for i in range(len(W)):
        counter = Counter(W[i])
        if counter:
            w = counter.most_common(1)[0][0]
            w = 0 if w < 0 else w
            W[i] = [int(digit) for digit in format(w, f"0{n}b")]
        else:
            empty_array_flag = True
            W[i] = [0] * n
    if empty_array_flag:
        print('存在空数组，补零')
    W = [item for w in W for item in w]

    W = W[:side_length ** 2 - 192]
    watermark = np.full((side_length, side_length), 1)
    detection_pattern = np.full((7, 7), 0)
    detection_pattern[1:6, 1:6] = np.full((5, 5), 1)
    detection_pattern[2:5, 2:5] = np.full((3, 3), 0)
    watermark[:7, :7] = watermark[:7, -7:] = watermark[-7:, :7] = detection_pattern
    watermark[0:8, 8: -8] = np.reshape(W[0:(side_length - 16) * 8], (8, side_length - 16))
    watermark[8:-8, :] = np.reshape(W[(side_length - 16) * 8:-(side_length - 8) * 8], (side_length - 16, side_length))
    watermark[-8:, 8:] = np.reshape(W[-(side_length - 8) * 8:], (8, side_length - 8))

    return original_shpfile, watermark


def extract(watermarked_shpfile_path, vr):
    import geopandas as gpd
    n = 4
    tau = 10 ** (-6)
    side_length = 45
    l = math.ceil((side_length ** 2 - 192) / n)
    R = Decimal('1e-7')

    watermarked_shpfile = gpd.read_file(watermarked_shpfile_path)

    watermarked_coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    coor_array = get_coor_array(watermarked_coor_nested, feature_type)
    coor_mean = np.mean(coor_array, axis=1)
    print(coor_mean, vr)
    ratio = np.mean(vr / coor_mean)
    print('倍数', ratio)
    argument = {'n': n, 'R': R, 'side_length': side_length, 'ratio': ratio, }
    original_shpfile, watermark = calculate_watermark_and_nc(watermarked_shpfile, l, argument)

    shp_output_folder = os.path.join(current_app.config['EXTRACTED_FOLDER'], 'shp')
    watermark_output_folder = os.path.join(current_app.config['EXTRACTED_FOLDER'], 'watermark')

    os.makedirs(shp_output_folder, exist_ok=True)
    os.makedirs(watermark_output_folder, exist_ok=True)

    output_shapefile_path = os.path.join(
        shp_output_folder,
        os.path.basename(watermarked_shpfile_path)
    )
    original_shpfile.to_file(output_shapefile_path)
    print("Shapefile创建完成，已保存为", output_shapefile_path)

    output_watermark_path = os.path.join(
        watermark_output_folder,
        f'{os.path.splitext(os.path.basename(watermarked_shpfile_path))[0]}.png'
    )
    Image.fromarray(watermark.astype(bool)).save(output_watermark_path)
    print("水印创建完成，已保存为", output_watermark_path)

    return output_shapefile_path, output_watermark_path