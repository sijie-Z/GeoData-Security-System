# import math
# import os
# import random
# import sys
# from collections import Counter
# from decimal import Decimal

# import geopandas as gpd
# import numpy as np
# from PIL import Image

# from algorithm.get_coor import get_coor_nested, get_coor_array
# # from select_file import select_file
# from algorithm.to_geodataframe import to_geodataframe
# from algorithm.NC import NC, image_to_array


# def watermark_extract(coor, coor_l, R, n):
#     """
#     对坐标嵌入水印
#     :param coor: 变换后的坐标
#     :param coor_l: 区域左下角顶点的坐标
#     :return:返回嵌入水印的坐标
#     """
#     x, y = coor
#     xl, yl = coor_l
#     x, y = x, y
#     xl, yl = xl, yl
#     # w = (x - xl) // ((xr - xl) / 2 ** n)
#     # original_x = xl + 2 ** n * (x - xl) - w * (xr - xl)
#     w = (x - xl) // (R / 2 ** n)
#     original_x = xl + 2 ** n * (x - xl) - w * R
#     original_y = y
#     # print(x, original_x, xl)
#     # print(coor_l, x, w, original_x)
#     return np.vstack([original_x, original_y]), int(w)


# def coor_process(coor, W, dis, argument):
#     """
#     对坐标进行处理
#     :param coor: 需要处理的坐标
#     :return: 嵌入水印的坐标
#     """
#     # print(coor)
#     n, R, side_length, ratio = argument.values()
#     random.seed(dis)

#     index = random.randint(0, len(W) - 1)
#     # print(dis,index)
#     coor = np.array([Decimal(str(x)) for x in coor])
#     # print(coor)
#     # print('------------------')
#     # print(coor)
#     coor_l = coor // R * R
#     original_coor, w = watermark_extract(coor, coor_l, R, n)
#     W[index].append(w)
#     return original_coor, W


# def coor_group_process(coor_group, W, argument):
#     """
#     对坐标组进行处理
#     :param coor_group:需要处理的坐标组
#     :return: 返回嵌入水印的坐标组
#     """
#     n, R, side_length, ratio = argument.values()
#     coor_group = coor_group * ratio
#     original_coor_group = np.array([[], []])
#     for i in range(coor_group.shape[1]):
#         coor = coor_group[:, i]
#         if i == coor_group.shape[1] - 1:
#             original_coor = coor[:, np.newaxis]
#         else:
#             dis = abs(coor[1] - coor_group[:, i + 1][1])
#             original_coor, W = coor_process(coor, W, dis, argument)
#         original_coor_group = np.concatenate((original_coor_group, original_coor), axis=1)

#     # print(coor_group)
#     # print(original_coor_group)
#     return original_coor_group, W


# def traversal_nested_coor_group(coor_nested, feature_type, W, argument):
#     """
#     对于多线、多面等情况，执行此函数
#     :param coor_nested: 所有要素组成的嵌套坐标数组
#     :param feature_type: 要素的类型
#     :return: 返回该要素更新后的嵌套坐标组
#     """
#     processed_x_nested = []
#     processed_y_nested = []
#     # 遍历要素中的每个坐标组
#     for feature_index in range(coor_nested.shape[1]):
#         coor_group = np.vstack(coor_nested[:, feature_index])
#         # 对坐标进行平移
#         processed_coor_group, W = coor_group_process(coor_group, W, argument)
#         # 如果要素为多面，则需要满足首位顶点的坐标相同
#         if (feature_type == 'MultiPolygon'
#                 and np.size(processed_coor_group) not in [0, 2]
#                 and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
#             processed_coor_group[:, -1] = processed_coor_group[:, 0]
#         processed_x_nested.append(processed_coor_group[0, :])
#         processed_y_nested.append(processed_coor_group[1, :])
#     return np.array([processed_x_nested, processed_y_nested], dtype=object), W


# def traversal_coor_group(coor_nested, shp_type, processed_shpfile, l, argument):
#     """
#     对所有要素进行遍历
#     :param coor_nested: 所有要素组成的嵌套坐标数组
#     :param shp_type: 每个要素类型组成的数组
#     :param processed_shpfile: 处理后的shp文件
#     :return: processed_shpfile
#     """
#     # ----------------定义局部变量----------------------
#     W = [[] for _ in range(l)]

#     # 遍历每个几何要素
#     for feature_index in range(coor_nested.shape[1]):
#         coor_group = np.vstack(coor_nested[:, feature_index])
#         if isinstance(coor_nested[:, feature_index][0], list):
#             continue
#         feature_type = shp_type[feature_index]
#         # 判断是否是多线、多面等的情况
#         if isinstance(coor_group[0, 0], np.ndarray):
#             processed_coor_group, W = traversal_nested_coor_group(coor_group, feature_type, W, argument)
#         else:
#             processed_coor_group, W = coor_group_process(coor_group, W, argument)
#             # 如果要素为面，则需要满足首尾顶点的坐标相同
#             if (feature_type == 'Polygon'
#                     and np.size(processed_coor_group) not in [0, 2]
#                     and not np.array_equal(processed_coor_group[:, 0], processed_coor_group[:, -1])):
#                 processed_coor_group[:, -1] = processed_coor_group[:, 0]
#         # 将改变的要素坐标组更新到geodataframe
#         processed_shpfile = to_geodataframe(processed_shpfile, feature_index, processed_coor_group,
#                                             shp_type[feature_index])
#     return processed_shpfile, W


# def calculate_watermark_and_nc(watermarked_shpfile, l, argument):
#     watermarked_coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
#     n, R, side_length, ratio = argument.values()

#     # -------------------------水印提取--------------------------------
#     # 遍历每个对象
#     original_shpfile = watermarked_shpfile.copy()
#     original_shpfile, W = traversal_coor_group(watermarked_coor_nested, feature_type, original_shpfile, l,
#                                                argument)

#     # 计算每个数组出现的次数
#     empty_array_flag = False  # 标志变量，用于跟踪是否存在空数组
#     for i in range(len(W)):
#         # 使用Counter统计每个数字的出现次数
#         counter = Counter(W[i])
#         if counter:
#             w = counter.most_common(1)[0][0]
#             w = 0 if w < 0 else w
#             W[i] = [int(digit) for digit in format(w, f"0{n}b")]  # 转换n位二进制
#         else:
#             empty_array_flag = True
#             W[i] = [0] * n
#     # 在循环结束后检查标志变量并打印消息
#     if empty_array_flag:
#         print('存在空数组，补零')
#     W = [item for w in W for item in w]

#     W = W[:side_length ** 2 - 192]  # 截断多余的长度
#     # print(W,len(W))
#     # 将计算后的数组填充到原数组中
#     watermark = np.full((side_length, side_length), 1)
#     detection_pattern = np.full((7, 7), 0)
#     detection_pattern[1:6, 1:6] = np.full((5, 5), 1)
#     detection_pattern[2:5, 2:5] = np.full((3, 3), 0)
#     watermark[:7, :7] = watermark[:7, -7:] = watermark[-7:, :7] = detection_pattern
#     watermark[0:8, 8: -8] = np.reshape(W[0:(side_length - 16) * 8], (8, side_length - 16))
#     watermark[8:-8, :] = np.reshape(W[(side_length - 16) * 8:-(side_length - 8) * 8], (side_length - 16, side_length))
#     watermark[-8:, 8:] = np.reshape(W[-(side_length - 8) * 8:], (8, side_length - 8))

#     return original_shpfile, watermark


# def extract(watermarked_shpfile_path,  vr):
#     # -------------------------预定义--------------------------------
#     n = 4  # 嵌入强度
#     tau = 10 ** (-6)  # 精度容差
#     side_length = 45  # 水印图像边长
#     l = math.ceil((side_length ** 2 - 192) / n)  # 水印长度
#     R = Decimal('1e-7')
#     # R = 1e-7

#     # -------------------------数据读取--------------------------------
#     watermarked_shpfile = gpd.read_file(watermarked_shpfile_path)

#     # -------------------------数据预处理--------------------------------

#     watermarked_coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
#     coor_array = get_coor_array(watermarked_coor_nested, feature_type)  # 将嵌套坐标数组合并成一个数组
#     coor_mean = np.mean(coor_array, axis=1)
#     print(coor_mean,vr)
#     ratio = np.mean(vr / coor_mean)
#     print('倍数', ratio)
#     argument = {'n': n, 'R': R, 'side_length': side_length, 'ratio': ratio, }
#     original_shpfile, watermark = calculate_watermark_and_nc(watermarked_shpfile, l, argument)

#     # # -------------------------数据输出--------------------------------
#     # # 创建文件夹
#     # folder_name = '..\\extract'
#     # if not os.path.exists(folder_name):
#     #     os.makedirs(folder_name)
#     #
#     # if not os.path.exists(f'{folder_name}\\shpfile'):
#     #     os.makedirs(f'{folder_name}\\shpfile')
#     #
#     # if not os.path.exists(f'{folder_name}\\watermark'):
#     #     os.makedirs(f'{folder_name}\\watermark')
#     #
#     # output_shapefile_path = f'{folder_name}\\shpfile\\{os.path.basename(watermarked_shpfile_path)}'
#     # # 将GeoDataFrame保存为shp文件
#     # original_shpfile.to_file(output_shapefile_path)
#     # print("Shapefile创建完成，已保存为", output_shapefile_path)
#     #
#     # # output_watermark_path = f'{folder_name}\\watermark\\{os.path.splitext(os.path.basename(watermarked_shpfile_path))[0]}.png'
#     #
#     # watermark_folder = r'E:\水印提取\watermark'
#     #
#     # output_watermark_path = os.path.join(
#     #     watermark_folder,
#     #     f'{os.path.splitext(os.path.basename(watermarked_shpfile_path))[0]}.png'
#     # )
#     # Image.fromarray(watermark.astype(bool)).save(output_watermark_path)
#     # print("水印创建完成，已保存为", output_watermark_path)
#     #
#     # return output_shapefile_path, output_watermark_path

#     # -------------------------数据输出--------------------------------
#     # 定义输出文件夹路径
#     shp_output_folder = r'E:\水印提取\shp'
#     watermark_output_folder = r'E:\水印提取\watermark'

#     # 创建文件夹
#     if not os.path.exists(shp_output_folder):
#         os.makedirs(shp_output_folder)

#     if not os.path.exists(watermark_output_folder):
#         os.makedirs(watermark_output_folder)

#     # 构建Shapefile的输出路径
#     output_shapefile_path = os.path.join(
#         shp_output_folder,
#         os.path.basename(watermarked_shpfile_path)
#     )
#     # 将GeoDataFrame保存为shp文件
#     original_shpfile.to_file(output_shapefile_path)
#     print("Shapefile创建完成，已保存为", output_shapefile_path)

#     # 构建水印文件的输出路径
#     output_watermark_path = os.path.join(
#         watermark_output_folder,
#         f'{os.path.splitext(os.path.basename(watermarked_shpfile_path))[0]}.png'
#     )
#     # 保存水印图像
#     Image.fromarray(watermark.astype(bool)).save(output_watermark_path)
#     print("水印创建完成，已保存为", output_watermark_path)

#     return output_shapefile_path, output_watermark_path




import math
import os
import random
import sys
from collections import Counter
from decimal import Decimal

import geopandas as gpd
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
    x, y = x, y
    xl, yl = xl, yl
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
    # -------------------------预定义--------------------------------
    n = 4
    tau = 10 ** (-6)
    side_length = 45
    l = math.ceil((side_length ** 2 - 192) / n)
    R = Decimal('1e-7')

    # -------------------------数据读取--------------------------------
    watermarked_shpfile = gpd.read_file(watermarked_shpfile_path)

    # -------------------------数据预处理--------------------------------
    watermarked_coor_nested, feature_type = get_coor_nested(watermarked_shpfile)
    coor_array = get_coor_array(watermarked_coor_nested, feature_type)
    coor_mean = np.mean(coor_array, axis=1)
    print(coor_mean, vr)
    ratio = np.mean(vr / coor_mean)
    print('倍数', ratio)
    argument = {'n': n, 'R': R, 'side_length': side_length, 'ratio': ratio, }
    original_shpfile, watermark = calculate_watermark_and_nc(watermarked_shpfile, l, argument)

    # -------------------------数据输出 (已修复) --------------------------------
    # 从 Flask 应用配置中获取正确的文件夹路径
    shp_output_folder = os.path.join(current_app.config['EXTRACTED_FOLDER'], 'shp')
    watermark_output_folder = os.path.join(current_app.config['EXTRACTED_FOLDER'], 'watermark')
    
    # 确保文件夹存在
    os.makedirs(shp_output_folder, exist_ok=True)
    os.makedirs(watermark_output_folder, exist_ok=True)

    # 构建Shapefile的输出路径
    output_shapefile_path = os.path.join(
        shp_output_folder,
        os.path.basename(watermarked_shpfile_path)
    )
    # 将GeoDataFrame保存为shp文件
    original_shpfile.to_file(output_shapefile_path)
    print("Shapefile创建完成，已保存为", output_shapefile_path)

    # 构建水印文件的输出路径
    output_watermark_path = os.path.join(
        watermark_output_folder,
        f'{os.path.splitext(os.path.basename(watermarked_shpfile_path))[0]}.png'
    )
    # 保存水印图像
    Image.fromarray(watermark.astype(bool)).save(output_watermark_path)
    print("水印创建完成，已保存为", output_watermark_path)

    return output_shapefile_path, output_watermark_path