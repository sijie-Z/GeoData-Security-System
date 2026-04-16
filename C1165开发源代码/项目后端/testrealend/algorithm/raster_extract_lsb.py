# algorithm/raster_extract_lsb.py

import cv2
import numpy as np

def extract(stego_array: np.ndarray, watermark_height: int, watermark_width: int) -> np.ndarray:
    watermarked_area = stego_array[:watermark_height, :watermark_width]
    extracted_watermark = (watermarked_area & 0b00000111) << 5
    
    return extracted_watermark