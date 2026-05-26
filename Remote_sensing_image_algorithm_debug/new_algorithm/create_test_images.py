# create_test_images.py
import os
import numpy as np
from PIL import Image

def create_test_images():
    # 创建images目录
    os.makedirs("images", exist_ok=True)
    
    # 创建彩色测试图像 (256x256)
    color_img = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    Image.fromarray(color_img).save("images/color_cover.png")
    
    # 创建灰度测试图像 (512x512)
    gray_img = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
    Image.fromarray(gray_img).save("images/gray_cover.png")
    
    # 创建大型遥感图像 (2304x1840)
    large_img = np.random.randint(0, 255, (1840, 2304, 3), dtype=np.uint8)
    Image.fromarray(large_img).save("images/large_cover.png")
    
    print("测试图像创建完成")

if __name__ == "__main__":
    create_test_images()