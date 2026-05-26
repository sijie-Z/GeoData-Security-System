import numpy as np
import imageio.v3 as imageio
from PIL import Image
import warnings

class ImagePreprocessor:
    """遥感图像预处理类，支持多种格式和预处理操作"""
    
    def __init__(self):
        self.supported_formats = ['.tif', '.tiff', '.png', '.jpg', '.jpeg', '.bmp']
    
    def load_image(self, image_path):
        """加载图像并转换为标准格式"""
        if not any(image_path.lower().endswith(fmt) for fmt in self.supported_formats):
            raise ValueError(f"Unsupported image format: {image_path}")
        
        print(f"Loading and preprocessing image: {image_path}")
        
        try:
            # 优先使用imageio.v3
            image_raw = imageio.imread(image_path)
        except Exception as e:
            print(f"Imageio failed, using Pillow fallback: {e}")
            try:
                with Image.open(image_path) as pil_img:
                    return self._process_pil_image(pil_img)
            except Exception as pil_e:
                raise IOError(f"Failed to read image {image_path}: {pil_e}")
        
        return self._process_raw_image(image_raw)
    
    def _process_pil_image(self, pil_img):
        """处理Pillow图像"""
        # 处理透明通道
        if pil_img.mode in ('RGBA', 'LA') or (pil_img.mode == 'P' and 'transparency' in pil_img.info):
            pil_img = pil_img.convert("RGBA")
            background = Image.new("RGB", pil_img.size, (255, 255, 255))
            background.paste(pil_img, mask=pil_img.split()[3])
            return np.array(background)
        else:
            return np.array(pil_img.convert("RGB"))
    
    def _process_raw_image(self, image_raw):
        """处理原始图像数据"""
        print(f"Original properties: Shape={image_raw.shape}, DataType={image_raw.dtype}")
        
        # 处理单通道图像
        if image_raw.ndim == 2:
            print("Detected grayscale image, converting to RGB")
            image_raw = np.stack([image_raw]*3, axis=-1)
        
        # 处理多通道图像
        if image_raw.shape[2] > 3:
            print(f"Detected multi-band image ({image_raw.shape[2]} bands)")
            if image_raw.shape[2] >= 3:
                # 默认取前三个波段
                image_raw = image_raw[:, :, :3]
                print("Using first three bands as RGB")
            else:
                # 对于波段数不足的情况，复制第一个波段
                image_raw = np.stack([image_raw[:, :, 0]]*3, axis=-1)
                print("Duplicating first band to create RGB")
        
        # 处理RGBA图像
        if image_raw.shape[2] == 4:
            print("Detected RGBA image, converting to RGB")
            alpha = image_raw[:, :, 3] if image_raw.shape[2] == 4 else None
            if alpha is not None and np.any(alpha < 255):
                # 处理半透明像素
                rgb = image_raw[:, :, :3]
                alpha = alpha[..., np.newaxis] / 255.0
                background = np.ones_like(rgb) * 255
                image_raw = (rgb * alpha + background * (1 - alpha)).astype(np.uint8)
            else:
                image_raw = image_raw[:, :, :3]
        
        # 数据类型转换
        dtype = image_raw.dtype
        if np.issubdtype(dtype, np.floating):
            print(f"Converting floating-point image (range: {image_raw.min():.2f}-{image_raw.max():.2f})")
            # 更稳健的浮点数处理
            if image_raw.max() > 1.0 or image_raw.min() < 0.0:
                # 百分位拉伸避免极端值影响
                p2, p98 = np.percentile(image_raw, [2, 98])
                image_raw = np.clip(image_raw, p2, p98)
                image_raw = (image_raw - p2) / (p98 - p2)
            image_raw = (np.clip(image_raw, 0, 1) * 255).astype(np.uint8)
        elif np.issubdtype(dtype, np.integer):
            max_val = np.iinfo(dtype).max
            if max_val > 255:
                print(f"Converting {dtype} image to 8-bit")
                image_raw = (image_raw.astype(np.float32) / max_val * 255).astype(np.uint8)
        
        print(f"Preprocessing complete: Shape={image_raw.shape}, DataType={image_raw.dtype}")
        return image_raw
    
    def resize_to_multiple(self, image, patch_size):
        """调整图像尺寸为patch_size的倍数"""
        h, w = image.shape[:2]
        new_h = ((h + patch_size - 1) // patch_size) * patch_size
        new_w = ((w + patch_size - 1) // patch_size) * patch_size
        
        if new_h != h or new_w != w:
            print(f"Resizing image: {h}x{w} -> {new_h}x{new_w}")
            # 使用边缘填充而不是缩放，以保持图像内容
            padded_image = np.pad(
                image, 
                ((0, new_h - h), (0, new_w - w), (0, 0)), 
                mode='edge'
            )
            return padded_image
        return image