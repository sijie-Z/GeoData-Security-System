import os
import torch
import numpy as np
from PIL import Image
from .model import IIWN
from .compressor import CustomRDH
from .utils import sha256_of_image_array, sha256_to_bitstream, download_model
from .bch import BCH
import random

class CRMark:
    """基于深度学习的可逆遥感图像水印算法"""
    
    MODEL_URLS = {
        "color_256_64": "https://github.com/chenoly/CRMark/releases/download/v1.0/crmark_color_size_256_bit_64.pth",
        "color_256_100": "https://github.com/chenoly/CRMark/releases/download/v1.0/crmark_color_size_256_bit_100.pth",
        "gray_512_256": "https://github.com/chenoly/CRMark/releases/download/v1.0/crmark_gray_size_512_bit_256.pth"
    }
    
    def __init__(self, model_mode="color_256_64", device=None, float64=False):
        # 验证模型模式
        assert model_mode in ["color_256_64", "color_256_100", "gray_512_256"], \
            "model_mode must be 'color_256_64', 'color_256_100' or 'gray_512_256'"
        
        # 设置设备
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.float64 = float64
        self.model_mode = model_mode
        
        # 设置模型参数
        if model_mode == "color_256_64":
            self.img_size = 256
            self.bit_length = 64
            self.channel_dim = 3
            self.bch_polynomial = 137
            self.bch_bits = 3
            self.fc = [64, 32, 16]  # 匹配预训练模型
        elif model_mode == "color_256_100":
            self.img_size = 256
            self.bit_length = 100
            self.channel_dim = 3
            self.bch_polynomial = 137
            self.bch_bits = 5
            self.fc = [64, 32, 16]  # 匹配预训练模型
        else:  # gray_512_256
            self.img_size = 512
            self.bit_length = 256
            self.channel_dim = 1
            self.bch_polynomial = 501
            self.bch_bits = 12
            self.fc = [128, 64, 32]  # 匹配预训练模型
        
        # 初始化BCH纠错码
        self.bch = BCH(self.bch_polynomial, self.bch_bits)
        
        # 设置缓存目录
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "crmark")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 加载模型
        self._load_model()
    
    def _load_model(self):
        """加载预训练模型"""
        model_filename = f"crmark_{self.model_mode}.pth"
        model_path = os.path.join(self.cache_dir, model_filename)
        
        # 如果模型不存在，则下载
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}, downloading...")
            download_model(self.MODEL_URLS[self.model_mode], model_path)
        
        # 加载模型
        load_dict = torch.load(model_path, map_location="cpu")
        
        # 设置精度
        if self.float64:
            torch.set_default_dtype(torch.float64)
        
        # 初始化可逆数据隐藏模块
        self.rdh = CustomRDH((self.img_size, self.img_size, self.channel_dim), self.device)
        
        # 初始化神经网络模型
        self.iIWN = IIWN(
            self.img_size, 
            self.channel_dim, 
            self.bit_length,
            load_dict['param_dict']['k'],
            load_dict['param_dict']['min_size'],
            self.fc  # 使用fc参数
        )
        
        # 加载状态字典
        self.iIWN.load_state_dict(load_dict['model_state_dict'])
        self.iIWN.to(self.device)
        self.iIWN.eval()
    
    def encode(self, cover_img, message):
        """嵌入文本水印到图像中"""
        cover_img = np.uint8(cover_img)
        
        # 验证消息长度和图像维度
        if self.model_mode == "color_256_64":
            assert len(message) == 5 and cover_img.ndim == 3, \
                "For color_256_64 model, message length should be 5 and image must be RGB"
        elif self.model_mode == "color_256_100":
            assert len(message) == 7 and cover_img.ndim == 3, \
                "For color_256_100 model, message length should be 7 and image must be RGB"
        else:
            assert len(message) == 20 and cover_img.ndim == 2, \
                "For gray_512_256 model, message length should be 20 and image must be grayscale"
        
        # 计算图像哈希
        cover_img_hash = sha256_of_image_array(cover_img)
        cover_img_hash_bitstream = sha256_to_bitstream(cover_img_hash)
        
        # 转换图像到张量
        if cover_img.ndim == 2:
            # 灰度图像添加通道维度
            cover_img = np.expand_dims(cover_img, axis=-1)
        
        cover_img_tensor = torch.from_numpy(cover_img).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        cover_img_tensor = cover_img_tensor.to(self.device)
        
        # 编码消息
        watermark = self.bch.encode(message)
        watermark += [random.randint(0, 1) for _ in range(self.bit_length - len(watermark))]
        secret_tensor = torch.tensor(watermark, dtype=torch.float32).unsqueeze(0).to(self.device)
        
        # 执行水印嵌入
        with torch.no_grad():
            if self.float64:
                cover_img_tensor = cover_img_tensor.to(torch.float64)
                secret_tensor = secret_tensor.to(torch.float64)
            
            overflow_stego, z = self.iIWN(cover_img_tensor, secret_tensor, True, False)
        
        # 处理隐写图像
        stego_255 = torch.round(overflow_stego * 255.0)
        
        # 使用RDH嵌入辅助位和哈希
        stego_np = stego_255.squeeze(0).permute(1, 2, 0).detach().cpu().numpy().astype(np.uint8)
        
        # 确保图像有正确的通道数
        if self.model_mode == "gray_512_256" and stego_np.shape[2] == 1:
            # 灰度图像移除通道维度
            stego_np = stego_np.squeeze(axis=-1)
        
        success, rdh_stego_img = self.rdh.embed(stego_np, cover_img_hash_bitstream)
        
        if not success:
            raise RuntimeError("Reversible embedding failed")
        
        return success, Image.fromarray(rdh_stego_img)
    
    def recover(self, stego_img):
        """从隐写图像中恢复原始图像和水印"""
        stego_img = np.uint8(stego_img)
        
        # 使用RDH提取数据
        success, clipped_stego_img, ext_auxbits = self.rdh.extract(stego_img)
        if not success:
            return True, None, None
        
        # 提取图像哈希
        cover_img_hash_bitstream = ext_auxbits[-256:]
        
        # 转换图像到张量
        if clipped_stego_img.ndim == 2:
            # 灰度图像添加通道维度
            clipped_stego_img = np.expand_dims(clipped_stego_img, axis=-1)
        
        stego_tensor = torch.from_numpy(clipped_stego_img).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        stego_tensor = stego_tensor.to(self.device)
        
        # 恢复原始图像和水印
        with torch.no_grad():
            if self.float64:
                stego_tensor = stego_tensor.to(torch.float64)
            
            rec_cover_tensor, rec_watermark = self.iIWN(stego_tensor, None, True, True)
        
        # 转换恢复的覆盖张量为图像
        rec_cover = rec_cover_tensor.squeeze(0).permute(1, 2, 0).detach().cpu().numpy()
        rec_cover = (rec_cover * 255).clip(0, 255).astype(np.uint8)
        
        # 确保图像有正确的通道数
        if self.model_mode == "gray_512_256" and rec_cover.shape[2] == 1:
            # 灰度图像移除通道维度
            rec_cover = rec_cover.squeeze(axis=-1)
        
        # 验证图像哈希
        rec_cover_img_hash = sha256_of_image_array(rec_cover)
        rec_cover_img_hash_bitstream = sha256_to_bitstream(rec_cover_img_hash)
        
        # 处理恢复的水印
        rec_watermark = torch.round(torch.clip(rec_watermark, 0., 1.))
        rec_watermark = rec_watermark[0].detach().cpu().numpy().astype(int).tolist()
        valid_part = rec_watermark[:(len(rec_watermark) // 8) * 8]
        success, decoded_data = self.bch.decode(valid_part)
        
        # 检查图像是否被攻击
        if np.array_equal(rec_cover_img_hash_bitstream, cover_img_hash_bitstream):
            return False, Image.fromarray(rec_cover), decoded_data
        else:
            return True, Image.fromarray(rec_cover), decoded_data