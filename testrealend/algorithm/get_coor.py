import logging
import numpy as np



def get_coor_nested(shpfile):
    """
    Getting coordinates makes each object an array and combines all arrays into one large array
    :param shpfile:
    :return: a list that has two-dimensional of coordinates and shp type
    """
    # 获取不同几何对象的坐标
    x_coords = []
    y_coords = []
    feature_type = []

    for geom in shpfile.geometry:
        # 对于空的Point，LineString来说保存为文件之后再读取得到的geom就是None
        if geom is not None:
            if geom.geom_type == 'Point':
                x_coords.append(np.array([geom.x]))
                y_coords.append(np.array([geom.y]))

            elif geom.geom_type == 'LineString':
                # 处理线几何对象的坐标
                x_coords.append(np.array(geom.xy[0]))
                y_coords.append(np.array(geom.xy[1]))

            elif geom.geom_type == 'MultiLineString':
                x_mult = []
                y_mult = []
                for line in geom.geoms:
                    coords = np.array(line.xy)
                    x_mult.append(coords[0])
                    y_mult.append(coords[1])
                x_coords.append(x_mult)
                y_coords.append(y_mult)

            elif geom.geom_type == 'Polygon':
                # 处理多边形几何对象的坐标
                # 处理多边形几何对象的外部环坐标
                if geom.interiors:
                    # 有内部环（孔洞）时，将外部环和内部环作为嵌套列表存储
                    x_mult = [np.array(geom.exterior.coords).T[0, :]]
                    y_mult = [np.array(geom.exterior.coords).T[1, :]]
                    for interior in geom.interiors:
                        interior_coords = np.array(interior.coords)
                        x_mult.append(interior_coords[:, 0])
                        y_mult.append(interior_coords[:, 1])
                    x_coords.append(x_mult)
                    y_coords.append(y_mult)
                else:
                    coords = geom.exterior.coords
                    x_coords.append(np.array(coords).T[0, :])
                    y_coords.append(np.array(coords).T[1, :])

            elif geom.geom_type == 'MultiPolygon':
                x_mult = []
                y_mult = []
                for polygon in geom.geoms:
                    x_mult.append(np.array(polygon.exterior.coords).T[0, :])
                    y_mult.append(np.array(polygon.exterior.coords).T[1, :])
                    for interior in polygon.interiors:
                        interior_coords = np.array(interior.coords)
                        x_mult.append(interior_coords[:, 0])
                        y_mult.append(interior_coords[:, 1])
                x_coords.append(x_mult)
                y_coords.append(y_mult)
            else:
                if geom.geom_type not in feature_type:
                    # 对于空的Point，LineString来说，未写入文件之前geom.geom_type为geometrycollection
                    logging.warning("Unparsed geometry type: %s", geom.geom_type)
            feature_type.append(geom.geom_type)

    coor_nested = np.array([x_coords, y_coords], dtype=object)
    return coor_nested, feature_type


def get_coor_array(coor_nested, shp_type):
    """
    将得到的嵌套数组，分别在下x和y方向进行合并
    :param coor_nested: shp数据顶点的嵌套数组
    :param shp_type: 要素类型的数组
    :return: 返回合并的数组
    """
    x_array = []
    y_array = []
    for i in range(coor_nested.shape[1]):
        x_val = coor_nested[0, i]
        y_val = coor_nested[1, i]
        # Skip empty features (all points deleted)
        if isinstance(x_val, (list, np.ndarray)) and len(x_val) == 0:
            continue
        if isinstance(x_val, np.ndarray) and x_val.ndim == 0 and len(x_val) == 0:
            continue
        # Multi-geometry (MultiPolygon, MultiLineString): list of arrays
        if shp_type[i] in ['MultiPolygon', 'MultiLineString']:
            parts_x = x_val if isinstance(x_val, list) else [x_val]
            parts_y = y_val if isinstance(y_val, list) else [y_val]
            for j in range(len(parts_x)):
                px = parts_x[j] if isinstance(parts_x[j], np.ndarray) else np.array(parts_x[j])
                py = parts_y[j] if isinstance(parts_y[j], np.ndarray) else np.array(parts_y[j])
                if px.size == 0 or py.size == 0:
                    continue
                coor_group = np.vstack((px, py))
                x_array = np.hstack((x_array, coor_group[0, :]))
                y_array = np.hstack((y_array, coor_group[1, :]))
        else:
            # Simple geometry (Point, LineString, Polygon without holes)
            x_arr = x_val if isinstance(x_val, np.ndarray) else np.array(x_val)
            y_arr = y_val if isinstance(y_val, np.ndarray) else np.array(y_val)
            if x_arr.size == 0 or y_arr.size == 0:
                continue
            x_array = np.hstack((x_array, x_arr))
            y_array = np.hstack((y_array, y_arr))
    coor_array = np.vstack((x_array, y_array))
    return coor_array


if __name__ == '__main__':
    import sys
    import geopandas as gpd
    if len(sys.argv) < 2:
        print("Usage: python get_coor.py <path_to_shpfile>")
        sys.exit(1)
    embed_shpfile = gpd.read_file(sys.argv[1])
    embed_coor_nested, file_type = get_coor_nested(embed_shpfile)
    embed_coor_array = get_coor_array(embed_coor_nested, file_type)
    logging.info("Coordinate array: %s", embed_coor_array)
