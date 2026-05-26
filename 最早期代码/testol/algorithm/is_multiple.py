# -*- coding: utf-8 -*-
# @Time    : 2024/3/22 16:06
# @Author  :Fivem
# @File    : is_multiple.py
# @Software: PyCharm
# @last modified:2024/3/22 16:06
import glob
import os
import sys

import geopandas as gpd

sys.path.append(r'/watermark/vector_process')


# from get_coor import get_coor_nested
# from select_file import select_folder


def is_multiple(path):
    print(f'当前处理的文件：{os.path.basename(path)}')
    shpfile = gpd.read_file(path)
    feature_type = list(shpfile.geom_type)
    indices = [index for index, value in enumerate(feature_type) if value in ['MultiPolygon', 'MultiLineString']]
    if len(indices) != 0:
        new_shp = shpfile.drop(indices)
        pathname = os.path.join(os.path.dirname(path), os.path.basename(path))
        new_shp.to_file(pathname)
        # new_shp.to_file(os.path.basename(path))
        print(
            f'共删除{len(indices)}条数据，对应索引号为：{indices}，类型为：{list(set([feature_type[i] for i in indices]))}')
        print(f'数据保存为{os.path.basename(path)}')
    print('-----------------------------------')


if __name__ == '__main__':
    # 数据读取
    # folder_path = select_folder()
    # folder_path = r"E:\矢量数据\数据\吴江区"
    folder_path = r"E:\矢量数据\数据\Coastline"
    # 遍历文件夹所有数据
    shapefiles = glob.glob(os.path.join(folder_path, '*.shp'))
    for shpfile_path in shapefiles:
        is_multiple(shpfile_path)

    # shpfile_path = select_file('select shpfile', [("shpfile", '*.shp')])
    # is_multiple(shpfile_path)
