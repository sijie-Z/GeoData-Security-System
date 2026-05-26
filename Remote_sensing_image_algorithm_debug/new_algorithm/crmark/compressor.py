import numpy as np
import torch

class CustomRDH:
    """可逆数据隐藏模块"""
    def __init__(self, image_shape, device):
        self.image_shape = image_shape
        self.device = device
        
    def embed(self, image, data):
        """嵌入辅助数据到图像中"""
        try:
            # 将数据转换为比特流
            data_bits = []
            for byte in data:
                for i in range(8):
                    data_bits.append((byte >> i) & 1)
            
            # 检查数据是否过大
            max_capacity = image.size // 8
            if len(data_bits) > max_capacity:
                raise ValueError(f"Data too large for image: {len(data_bits)} > {max_capacity}")
            
            # 嵌入数据到最低有效位
            image_flat = image.flatten()
            for i, bit in enumerate(data_bits):
                # 清除最低位
                image_flat[i] = (image_flat[i] & 0xFE) | bit
            
            # 恢复图像形状
            return True, image_flat.reshape(image.shape)
        except Exception as e:
            print(f"Reversible embedding failed: {e}")
            return False, image
    
    def extract(self, image):
        """从图像中提取辅助数据"""
        try:
            # 提取最低有效位
            image_flat = image.flatten()
            data_bits = []
            for i in range(len(image_flat)):
                bit = image_flat[i] & 1
                data_bits.append(bit)
                
                # 恢复原始像素值
                image_flat[i] = (image_flat[i] & 0xFE) | bit
            
            # 将比特流转换为字节
            data_bytes = []
            for i in range(0, len(data_bits), 8):
                byte = 0
                for j in range(8):
                    if i+j < len(data_bits):
                        byte |= (data_bits[i+j] << j)
                data_bytes.append(byte)
            
            return True, image_flat.reshape(image.shape), data_bytes
        except Exception as e:
            print(f"Reversible extraction failed: {e}")
            return False, image, []