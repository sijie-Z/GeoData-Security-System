import cv2
import numpy as np

def embed(host_array: np.ndarray, watermark_array: np.ndarray) -> np.ndarray:
    """
    一个高效的LSB水印嵌入引擎，使用Numpy向量化操作。
    它将水印1:1嵌入到载体的左上角。
    
    Args:
        host_array (np.ndarray): 载体图像 (8-bit BGR).
        watermark_array (np.ndarray): 水印图像 (8-bit BGR).
        
    Returns:
        np.ndarray: 带水印的图像 (8-bit BGR).
    """
    h_host, w_host, _ = host_array.shape
    h_wm, w_wm, _ = watermark_array.shape

    if h_wm > h_host or w_wm > w_host:
        raise ValueError("水印图像的尺寸不能大于载体图像。")

    stego_img = host_array.copy()
    
    target_area = stego_img[:h_wm, :w_wm]
    
    host_cleared = target_area & 0b11111000
    watermark_shifted = (watermark_array & 0b11100000) >> 5
    embedded_area = host_cleared | watermark_shifted
    
    stego_img[:h_wm, :w_wm] = embedded_area
    
    return stego_img