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

def is_multiple(path, output_path=None):
    """Convert MultiPolygon/MultiLineString to single-part geometries.

    Args:
        path: Input shapefile path.
        output_path: Output path. If None, appends '_single' to the filename.
                     The original file is NEVER overwritten.
    Returns:
        Path to the output shapefile, or None if no conversion was needed.
    """
    import logging
    import geopandas as gpd
    from shapely.geometry import MultiPolygon, MultiLineString
    logging.info('当前处理的文件：%s', os.path.basename(path))
    try:
        shpfile = gpd.read_file(path)
        feature_type = list(shpfile.geom_type)
        indices = [index for index, value in enumerate(feature_type) if value in ['MultiPolygon', 'MultiLineString']]

        if indices:
            converted = 0
            for idx in indices:
                geom = shpfile.at[idx, 'geometry']
                if geom is None:
                    continue
                if isinstance(geom, MultiPolygon) and len(geom.geoms) > 0:
                    shpfile.at[idx, 'geometry'] = geom.geoms[0]
                    converted += 1
                elif isinstance(geom, MultiLineString) and len(geom.geoms) > 0:
                    shpfile.at[idx, 'geometry'] = geom.geoms[0]
                    converted += 1
            if output_path is None:
                base, ext = os.path.splitext(path)
                output_path = f"{base}_single{ext}"
            shpfile.to_file(output_path)
            logging.info('共转换 %d 条多部分几何为单部分，对应索引号为：%s，类型为：%s',
                         converted, indices, list(set([feature_type[i] for i in indices])))
            logging.info('转换后数据保存为：%s', os.path.basename(output_path))
            return output_path
        else:
            logging.info('文件中不含多部分几何类型，无需处理。')
            return path
    except Exception as e:
        logging.error("处理文件 %s 时出错: %s", path, e)
        return None
    finally:
        logging.info('-----------------------------------')

def main():
    import logging
    folder_path = os.environ.get('SHP_FOLDER', os.path.join(os.getcwd(), 'data'))

    # 遍历文件夹所有数据
    shapefiles = glob.glob(os.path.join(folder_path, '*.shp'))
    if not shapefiles:
        logging.warning("在 %s 目录下没有找到任何 .shp 文件。", folder_path)
        return

    for shpfile_path in shapefiles:
        is_multiple(shpfile_path)

if __name__ == '__main__':
    main()