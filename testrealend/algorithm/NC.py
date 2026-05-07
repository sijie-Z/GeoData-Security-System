# import os
# import sys

# import numpy as np
# from PIL import Image

# script = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # dirname:上一级路径
# path = os.path.join(script, 'vector_process')
# sys.path.append(path)
# # from select_file import select_file


# def image_to_array(path):
#     image = Image.open(path)  # 替换为你的PNG格式二值图像文件路径
#     # 转换为NumPy数组
#     image_array = np.array(image).astype(int)
#     return image_array


# def NC(original_watermark, extract_watermark):
#     """
#     calculate normalized correlation(NC)
#     :param original_watermark:
#     :param extract_watermark:
#     :return:
#     """
#     if original_watermark.shape != extract_watermark.shape:
#         exit('Input vectors must be the same size!')
#         # print('Input vectors not be the same size!')
#         # if original_watermark.shape[0] < extract_watermark.shape[0]:
#         #     # 原始水印长度较小，补零
#         #     pad_width = extract_watermark.shape[0] - original_watermark.shape[0]
#         #     original_watermark = np.pad(original_watermark, [(0, pad_width)], mode='constant')
#         # else:
#         #     # 提取的水印长度较小，补零
#         #     pad_width = original_watermark.shape[0] - extract_watermark.shape[0]
#         #     extract_watermark = np.pad(extract_watermark, [(0, pad_width)], mode='constant')
#     elif ~np.all((original_watermark == 0) | (original_watermark == 1)) | ~np.all(
#             (extract_watermark == 0) | (extract_watermark == 1)):
#         exit('The input must be a binary image logical value image!')

#     result = ~(original_watermark ^ extract_watermark)
#     return (result == -1).sum() / original_watermark.size


# if __name__ == "__main__":
#     original_watermark_path = select_file('select the original watermark',
#                                           [("watermark file", "*.png *.jpg")])  # 读取PNG图像文件

#     original_watermark = image_to_array(original_watermark_path)
#     extract_watermark_path = select_file('select the extract watermark', [("watermark file", "*.png *.jpg")])
#     extract_watermark = image_to_array(extract_watermark_path)
#     print(NC(original_watermark, extract_watermark))



import os
import sys
import numpy as np
from PIL import Image

# 假设该模块所在的包结构已被正确配置，不依赖于修改 sys.path
# from .select_file import select_file  # 这行代码在生产环境中应该这样写

def image_to_array(path):
    # ... (代码不变)
    image = Image.open(path)
    image_array = np.array(image).astype(int)
    return image_array

def NC(original_watermark, extract_watermark):
    if original_watermark.shape != extract_watermark.shape:
        raise ValueError('输入图像尺寸不一致！')

    if not (np.all(np.isin(original_watermark, [0, 1])) and np.all(np.isin(extract_watermark, [0, 1]))):
        raise ValueError('输入图像必须是二值图像（0或1）！')

    # 修正 NC 公式，计算相同像素的比率
    # 转换为布尔值进行比较
    same_pixels = (original_watermark.astype(bool) == extract_watermark.astype(bool))
    return np.sum(same_pixels) / original_watermark.size


if __name__ == "__main__":
    # 这里的路径是示例，用于演示如何通过参数传递
    original_watermark_path = "path/to/original_watermark.png"
    extract_watermark_path = "path/to/extracted_watermark.png"
    
    try:
        original_watermark = image_to_array(original_watermark_path)
        extract_watermark = image_to_array(extract_watermark_path)
        print(f"NC 值: {NC(original_watermark, extract_watermark)}")
    except FileNotFoundError:
        print("错误: 找不到测试文件。请替换为实际文件路径。")
    except ValueError as e:
        print(f"错误: {e}")