import numpy as np
import hashlib
import os
import requests
from tqdm import tqdm

def sha256_of_image_array(image_array):
    """计算图像数组的SHA256哈希值"""
    return hashlib.sha256(image_array.tobytes()).hexdigest()

def sha256_to_bitstream(sha256_hash):
    """将SHA256哈希转换为比特流"""
    bitstream = []
    for char in sha256_hash:
        byte = int(char, 16)
        for i in range(4):
            bitstream.append((byte >> i) & 1)
    return bitstream

def download_model(url, save_path):
    """从GitHub下载预训练模型"""
    print(f"Downloading model from: {url}")
    
    # 创建目录
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        if total_size == 0:
            raise ValueError("Invalid content length")
        
        with open(save_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=os.path.basename(save_path)) as pbar:
                for data in response.iter_content(chunk_size=1024):
                    f.write(data)
                    pbar.update(len(data))
        
        print(f"Model downloaded successfully to: {save_path}")
        return True
    except Exception as e:
        print(f"Model download failed: {e}")
        print(f"Please download the model manually from: {url}")
        print(f"And place it at: {save_path}")
        return False