# from decimal import Decimal
# import geopandas as gpd
# import matplotlib.pyplot as plt
# import numpy as np
# from shapely.geometry import LineString, Point, Polygon, MultiPolygon, MultiLineString

# def to_geodataframe(dataframe, index, coor_group, shpfile_type):
#     if shpfile_type == 'Point':
#         if len(coor_group[1]) > 0:
#             dataframe.loc[index, 'geometry'] = Point([(Decimal(str(x)), Decimal(str(y))) for x, y in zip(coor_group[0], coor_group[1])])
#         else:
#             dataframe.loc[index, 'geometry'] = None  # Or set to a default point if desired

#     elif shpfile_type == 'LineString':
#         if len(coor_group[1]) > 1:
#             dataframe.loc[index, 'geometry'] = LineString([(Decimal(str(x)), Decimal(str(y))) for x, y in zip(coor_group[0], coor_group[1])])
#         else:
#             dataframe.loc[index, 'geometry'] = None

#     elif shpfile_type == 'MultiLineString':
#         lines = [LineString([(Decimal(str(x)), Decimal(str(y))) for x, y in zip(cg[0], cg[1])]) for cg in coor_group if cg[1].size > 1]
#         non_empty_lines = [line for line in lines if not line.is_empty]
#         if non_empty_lines:
#             dataframe.loc[index, 'geometry'] = MultiLineString(non_empty_lines)
#         else:
#             dataframe.loc[index, 'geometry'] = None

#     elif shpfile_type == 'Polygon':
#         if len(coor_group[1]) > 2:
#             dataframe.loc[index, 'geometry'] = Polygon([(Decimal(str(x)), Decimal(str(y))) for x, y in zip(coor_group[0], coor_group[1])])
#         else:
#             dataframe.loc[index, 'geometry'] = None

#     elif shpfile_type == 'MultiPolygon':
#         polygons = [Polygon([(Decimal(str(x)), Decimal(str(y))) for x, y in zip(cg[0], cg[1])]) for cg in coor_group if cg[1].size > 2]
#         if polygons:
#             dataframe.loc[index, 'geometry'] = MultiPolygon(polygons)
#         else:
#             dataframe.loc[index, 'geometry'] = None

#     else:
#         print("存在未写入的数组类型")

#     return dataframe

# if __name__ == "__main__":
#     gdf = gpd.GeoDataFrame(geometry=[None, None], crs="EPSG:4326")  # Specify CRS if needed
#     coorArray = [(73.85844152801786, 15.940917473114041)]
#     gdf.loc[1, 'geometry'] = Point(coorArray)
#     print(gdf)
#     gdf.plot()
#     plt.show()



import numpy as np
import geopandas as gpd
from decimal import Decimal
from shapely.geometry import (
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon
)

def _convert_coords_to_decimal(coords_list):
    """
    将坐标列表中的浮点数转换为 Decimal 类型。
    """
    return [(Decimal(str(x)), Decimal(str(y))) for x, y in coords_list]

def to_geodataframe(dataframe, index, coor_nested, shpfile_type):
    """
    将嵌套坐标数组转换为 GeoDataFrame 的几何对象。
    """
    # 提取 x 和 y 坐标
    x_coords = coor_nested[0]
    y_coords = coor_nested[1]
    
    # 检查坐标数组是否为空或只有一个元素
    # 修改后的代码，使用 .size 属性安全地检查数组是否为空
    if x_coords.size == 0 or y_coords.size == 0:
        dataframe.loc[index, 'geometry'] = None
        return dataframe

    if shpfile_type == 'Point':
        if x_coords.size > 0:
            dataframe.loc[index, 'geometry'] = Point(Decimal(str(x_coords[0])), Decimal(str(y_coords[0])))
        else:
            dataframe.loc[index, 'geometry'] = None

    elif shpfile_type == 'LineString':
        if x_coords.size > 1:
            points = _convert_coords_to_decimal(zip(x_coords, y_coords))
            dataframe.loc[index, 'geometry'] = LineString(points)
        else:
            dataframe.loc[index, 'geometry'] = None

    elif shpfile_type == 'MultiLineString':
        lines = []
        if isinstance(x_coords[0], list) or isinstance(x_coords[0], np.ndarray):
            for i in range(len(x_coords)):
                if x_coords[i].size > 1:
                    points = _convert_coords_to_decimal(zip(x_coords[i], y_coords[i]))
                    lines.append(LineString(points))
        else:
            if x_coords.size > 1:
                points = _convert_coords_to_decimal(zip(x_coords, y_coords))
                lines.append(LineString(points))

        if lines:
            dataframe.loc[index, 'geometry'] = MultiLineString(lines)
        else:
            dataframe.loc[index, 'geometry'] = None

    elif shpfile_type == 'Polygon':
        if x_coords.size > 2:
            exterior_coords = _convert_coords_to_decimal(zip(x_coords, y_coords))
            dataframe.loc[index, 'geometry'] = Polygon(exterior_coords)
        else:
            dataframe.loc[index, 'geometry'] = None

    elif shpfile_type == 'MultiPolygon':
        polygons = []
        if isinstance(x_coords[0], list) or isinstance(x_coords[0], np.ndarray):
            for i in range(len(x_coords)):
                if x_coords[i].size > 2:
                    exterior_coords = _convert_coords_to_decimal(zip(x_coords[i], y_coords[i]))
                    polygons.append(Polygon(exterior_coords))
        else:
            if x_coords.size > 2:
                exterior_coords = _convert_coords_to_decimal(zip(x_coords, y_coords))
                polygons.append(Polygon(exterior_coords))

        if polygons:
            dataframe.loc[index, 'geometry'] = MultiPolygon(polygons)
        else:
            dataframe.loc[index, 'geometry'] = None
    
    else:
        dataframe.loc[index, 'geometry'] = None
        print(f"警告: 存在未写入或无法识别的数组类型: {shpfile_type}")

    return dataframe