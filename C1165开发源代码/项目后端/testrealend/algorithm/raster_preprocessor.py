import numpy as np
import imageio.v2 as imageio
from PIL import Image

def load_as_rgb_array(image_path: str) -> np.ndarray:
    """
    一个健壮的函数，能加载各种图像格式 (PNG, JPG, BMP, TIF, GeoTIFF)
    并将其统一转换为标准的8位、3通道的RGB Numpy数组。
    """
    try:
        # imageio结合tifffile和imagecodecs，是读取科学数据的最佳选择
        image_raw = imageio.imread(image_path)
    except Exception:
        # Pillow作为备用，擅长处理普通图像格式
        pil_img = Image.open(image_path)
        return np.array(pil_img.convert("RGB"))

    # --- 数据类型转换 (处理高位深度和浮点数) ---
    if 'float' in str(image_raw.dtype):
        min_val, max_val = np.percentile(image_raw, [2, 98])
        clipped_raw = np.clip(image_raw, min_val, max_val)
        if (max_val - min_val) > 0:
            normalized_float = (clipped_raw - min_val) / (max_val - min_val)
        else:
            normalized_float = np.zeros_like(clipped_raw, dtype=np.float32)
        image_uint8 = (normalized_float * 255).astype(np.uint8)
    elif image_raw.dtype == 'uint16':
        image_uint8 = (image_raw / 65535.0 * 255).astype(np.uint8)
    elif image_raw.dtype == 'uint8':
        image_uint8 = image_raw
    else:
        raise TypeError(f"Unsupported input data type: {image_raw.dtype}")

    # --- 通道处理 (灰度, RGBA, 多波段) ---
    if image_uint8.ndim == 2:
        image_uint8 = np.stack([image_uint8]*3, axis=-1)
    
    if image_uint8.shape[2] == 4:
        image_uint8 = np.array(Image.fromarray(image_uint8).convert("RGB"))
    elif image_uint8.shape[2] > 3:
        band_indices = [3, 2, 1] 
        image_uint8 = image_uint8[:, :, band_indices]

    return image_uint8