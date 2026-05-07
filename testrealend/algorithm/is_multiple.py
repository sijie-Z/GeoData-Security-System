# # -*- coding: utf-8 -*-
# # @Time    : 2024/3/22 16:06
# # @Author  :Fivem
# # @File    : is_multiple.py
# # @Software: PyCharm
# # @last modified:2024/3/22 16:06
# import glob
# import os
# import sys

# import geopandas as gpd

# sys.path.append(r'/watermark/vector_process')


# # from get_coor import get_coor_nested
# # from select_file import select_folder


# def is_multiple(path):
#     print(f'当前处理的文件：{os.path.basename(path)}')
#     shpfile = gpd.read_file(path)
#     feature_type = list(shpfile.geom_type)
#     indices = [index for index, value in enumerate(feature_type) if value in ['MultiPolygon', 'MultiLineString']]
#     if len(indices) != 0:
#         new_shp = shpfile.drop(indices)
#         pathname = os.path.join(os.path.dirname(path), os.path.basename(path))
#         new_shp.to_file(pathname)
#         # new_shp.to_file(os.path.basename(path))
#         print(
#             f'共删除{len(indices)}条数据，对应索引号为：{indices}，类型为：{list(set([feature_type[i] for i in indices]))}')
#         print(f'数据保存为{os.path.basename(path)}')
#     print('-----------------------------------')


# if __name__ == '__main__':
#     # 数据读取
#     # folder_path = select_folder()
#     # folder_path = r"E:\矢量数据\数据\吴江区"
#     folder_path = r"E:\矢量数据\数据\Coastline"
#     # 遍历文件夹所有数据
#     shapefiles = glob.glob(os.path.join(folder_path, '*.shp'))
#     for shpfile_path in shapefiles:
#         is_multiple(shpfile_path)

#     # shpfile_path = select_file('select shpfile', [("shpfile", '*.shp')])
#     # is_multiple(shpfile_path)



import glob
import os
import sys

# 动态获取当前脚本所在目录
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# 假设 vector_process 位于项目根目录下
# 这里需要你根据你的项目结构调整
# 例如，如果 yingbianma 是你的项目根目录，并且 vector_process 在其中，你可以这样做：
project_root = os.path.dirname(current_script_dir) 
# 如果你的文件结构是 D:\Desktop\MyProjects\yingbianma\is_multiple.py
# 那么 project_root 将是 D:\Desktop\MyProjects
sys.path.append(project_root)

# 然后你可以正常导入你的模块
# 例如：from vector_process import some_module

def is_multiple(path):
    import geopandas as gpd
    print(f'当前处理的文件：{os.path.basename(path)}')
    try:
        shpfile = gpd.read_file(path)
        feature_type = list(shpfile.geom_type)
        indices = [index for index, value in enumerate(feature_type) if value in ['MultiPolygon', 'MultiLineString']]
        
        if indices:
            new_shp = shpfile.drop(indices)
            pathname = os.path.join(os.path.dirname(path), os.path.basename(path))
            new_shp.to_file(pathname)
            print(f'共删除 {len(indices)} 条数据，对应索引号为：{indices}，类型为：{list(set([feature_type[i] for i in indices]))}')
            print(f'数据已覆盖保存为：{os.path.basename(path)}')
        else:
            print('文件中不含多部分几何类型，无需处理。')
    except Exception as e:
        print(f"处理文件 {path} 时出错: {e}")
    finally:
        print('-----------------------------------')

def main():
    # 数据读取，使用你提供的硬编码路径
    folder_path = r"D:\Desktop\MyProjects\yingbianma"  
    
    # 遍历文件夹所有数据
    shapefiles = glob.glob(os.path.join(folder_path, '*.shp'))
    if not shapefiles:
        print(f"在 {folder_path} 目录下没有找到任何 .shp 文件。")
        return
        
    for shpfile_path in shapefiles:
        is_multiple(shpfile_path)

if __name__ == '__main__':
    main()