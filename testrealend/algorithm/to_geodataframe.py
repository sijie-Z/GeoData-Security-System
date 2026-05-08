import logging
import numpy as np
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
        logging.warning("Unrecognized geometry type: %s", shpfile_type)

    return dataframe