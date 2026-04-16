import geopandas as gpd
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
    # for geom in shpfile.geometry:
    #     # 对于空的Point，LineString来说 保存为文件之后 再读取得到的geom就是None
    #     if geom != None:
    #         if geom.type == 'Point':
    #             x_coords.append(np.array([geom.x]))
    #             y_coords.append(np.array([geom.y]))
    #
    #         elif geom.type == 'LineString':
    #             # 处理线几何对象的坐标
    #             x_coords.append(np.array(geom.xy[0]))
    #             y_coords.append(np.array(geom.xy[1]))
    #
    #         elif geom.type == 'MultiLineString':
    #             x_mult = []
    #             y_mult = []
    #             for line in geom.geoms:
    #                 coords = np.array(line.xy)
    #                 x_mult.append(coords[0])
    #                 y_mult.append(coords[1])
    #             x_coords.append(x_mult)
    #             y_coords.append(y_mult)
    #
    #         elif geom.type == 'Polygon':
    #             # 处理多边形几何对象的坐标
    #             # 处理多边形几何对象的外部环坐标
    #             coords = geom.exterior.coords
    #             x_coords.append(np.array(coords).T[0, :])
    #             y_coords.append(np.array(coords).T[1, :])
    #             # todo：内部环没处理
    #             # # 处理多边形几何对象的内部环坐标
    #             # for interior in geom.interiors:
    #             #     print('是')
    #             #     interior_coords = np.array(interior.coords)
    #             #     x_coords.append(interior_coords[:, 0])
    #             #     y_coords.append(interior_coords[:, 1])
    #
    #         elif geom.type == 'MultiPolygon':
    #             x_mult = []
    #             y_mult = []
    #             for polygon in geom.geoms:
    #                 coords = polygon.exterior.coords
    #                 x_mult.append(np.array(coords).T[0, :])
    #                 y_mult.append(np.array(coords).T[1, :])
    #                 #     interior_coords = np.array(interior.coords)
    #                 #     np.append(x_mult, interior_coords[:, 0])
    #                 #     np.append(y_mult, interior_coords[:, 1])
    #             x_coords.append(x_mult)
    #             y_coords.append(y_mult)
    #         else:
    #             if geom.type not in feature_type:
    #                 # 对于空的Point，LineString来说，未写入文件之前 geom.type为geometrycollection
    #                 print(f"\n存在未解析类型{geom.type}")
    #         feature_type.append(geom.type)
    #     coor_nested = np.array([x_coords, y_coords], dtype=object)
    # return coor_nested, feature_type

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
                coords = geom.exterior.coords
                x_coords.append(np.array(coords).T[0, :])
                y_coords.append(np.array(coords).T[1, :])
                # todo：内部环没处理
                # # 处理多边形几何对象的内部环坐标
                # for interior in geom.interiors:
                #     print('是')
                #     interior_coords = np.array(interior.coords)
                #     x_coords.append(interior_coords[:, 0])
                #     y_coords.append(interior_coords[:, 1])

            elif geom.geom_type == 'MultiPolygon':
                x_mult = []
                y_mult = []
                for polygon in geom.geoms:
                    coords = polygon.exterior.coords
                    x_mult.append(np.array(coords).T[0, :])
                    y_mult.append(np.array(coords).T[1, :])
                    #     interior_coords = np.array(interior.coords)
                    #     np.append(x_mult, interior_coords[:, 0])
                    #     np.append(y_mult, interior_coords[:, 1])
                x_coords.append(x_mult)
                y_coords.append(y_mult)
            else:
                if geom.geom_type not in feature_type:
                    # 对于空的Point，LineString来说，未写入文件之前geom.geom_type为geometrycollection
                    print(f"\n存在未解析类型{geom.geom_type}")
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
    # 遍历数组中的每个要素
    for i in range(coor_nested.shape[1]):
        # todo 一组数据的所有点都被删除后 ，会报错
        # 判断是否是要素内部是否还是数组 即判断是否是MultiPolygon等
        try:
            if isinstance(coor_nested[:, i][0][0], np.ndarray):
                if len(coor_nested[:, i][0]) == 0:
                    continue
                else:
                    for j in range(len(coor_nested[:, i][0])):
                        coor_group = np.vstack((coor_nested[:, i][0][j], coor_nested[:, i][1][j]))
                        x_array = np.hstack((x_array, coor_group[0, :]))
                        y_array = np.hstack((y_array, coor_group[1, :]))
            else:
                x_array = np.hstack((x_array, coor_nested[0, i]))
                y_array = np.hstack((y_array, coor_nested[1, i]))
        # 如果存在indexError 即该要素为空，然后再判断 shp_type，如果先判断这个的话，会存在问题
        # todo:什么问题 一个数组会嵌套数组 但进入else判断中
        except IndexError as e:
            print(e)
            if shp_type[i] in ['MultiPolygon', 'MultiLineString']:
                if len(coor_nested[:, i][0]) == 0:
                    continue
                else:
                    for j in range(len(coor_nested[:, i][0])):
                        coor_group = np.vstack((coor_nested[:, i][0][j], coor_nested[:, i][1][j]))
                        x_array = np.hstack((x_array, coor_group[0, :]))
                        y_array = np.hstack((y_array, coor_group[1, :]))
            else:
                x_array = np.hstack((x_array, coor_nested[0, i]))
                y_array = np.hstack((y_array, coor_nested[1, i]))
    coor_array = np.vstack((x_array, y_array))
    return coor_array


if __name__ == '__main__':
    embed_shpfile_path = select_file('select embed shpfile', [("shpfile", '*.shp')])


    embed_shpfile = gpd.read_file(embed_shpfile_path)
    embed_coor_nested, file_type = get_coor_nested(embed_shpfile)
    embed_coor_array = get_coor_array(embed_coor_nested, file_type)
    print(embed_coor_array)
