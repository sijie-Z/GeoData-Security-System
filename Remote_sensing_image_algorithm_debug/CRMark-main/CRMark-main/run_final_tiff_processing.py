# =======================================================
#               FINAL TIFF PROCESSING SCRIPT (Architectural Fix)
# =======================================================
print("--- EXECUTING run_final_tiff_processing.py (Architectural Fix) ---")

import os
import math
import numpy as np
from PIL import Image
from crmark import CRMark
import random
import imageio.v2 as imageio
import gc
from tqdm import tqdm

def process_tiff_image_final(
    crmark_instance: CRMark,
    input_path: str,
    output_path_stego: str,
    output_path_recovered: str,
    watermark_bits: list
):
    print(f"Loading large TIFF image from: {input_path}")
    large_image_raw = imageio.imread(input_path)
    print(f"Original image properties: Shape={large_image_raw.shape}, DataType={large_image_raw.dtype}")

    # --- 1. 数据预处理 ---
    if 'float' in str(large_image_raw.dtype):
        min_val, max_val = np.percentile(large_image_raw, [2, 98])
        clipped_raw = np.clip(large_image_raw, min_val, max_val)
        normalized_float = (clipped_raw - min_val) / (max_val - min_val) if (max_val - min_val) > 0 else np.zeros_like(clipped_raw, dtype=np.float32)
    elif large_image_raw.dtype == 'uint16':
        normalized_float = large_image_raw.astype(np.float32) / 65535.0
    elif large_image_raw.dtype == 'uint8':
        normalized_float = large_image_raw.astype(np.float32) / 255.0
    else:
        raise ValueError(f"Unsupported TIFF data type: {large_image_raw.dtype}")
        
    image_uint8 = (normalized_float * 255).astype(np.uint8)
    
    if image_uint8.ndim == 3 and image_uint8.shape[2] > 3:
        band_indices = [3, 2, 1]
        image_uint8 = image_uint8[:, :, band_indices]

    original_h, original_w, _ = image_uint8.shape
    
    # --- 2. 准备工作画布 (预填充) ---
    patch_size = crmark_instance.img_size
    padded_h = math.ceil(original_h / patch_size) * patch_size
    padded_w = math.ceil(original_w / patch_size) * patch_size
    
    padded_array = np.pad(image_uint8, 
                          ((0, padded_h - original_h), (0, padded_w - original_w), (0, 0)), 
                          'edge')
    
    # --- 3. 嵌入水印 ---
    print("\n--- Starting Encoding Process ---")
    print(f"Canvas size for watermarking: {padded_array.shape}")
    
    num_patches = (padded_h // patch_size) * (padded_w // patch_size)
    required_bits = num_patches * crmark_instance.bit_length
    
    if len(watermark_bits) < required_bits:
        watermark_bits.extend([0] * (required_bits - len(watermark_bits)))
    else:
        watermark_bits = watermark_bits[:required_bits]
        
    print(f"Embedding {len(watermark_bits)} bits into the canvas...")
    
    success, stego_canvas_array = embed_on_canvas(crmark_instance, padded_array, watermark_bits)
    
    if not success:
        print("FATAL: Embedding on the full canvas failed.")
        return

    stego_final_array = stego_canvas_array[:original_h, :original_w, :]
    Image.fromarray(stego_final_array).save(output_path_stego)
    print(f"Stego image saved to: {output_path_stego}")

    del padded_array
    gc.collect()

    # --- 4. 恢复水印 ---
    print("\n--- Starting Recovery Process ---")
    success_rec, recovered_canvas_array, extracted_bits = recover_from_canvas(crmark_instance, stego_canvas_array)
    
    if not success_rec:
        print("FATAL: Recovery from the full canvas failed.")
        return
        
    recovered_final_array = recovered_canvas_array[:original_h, :original_w, :]
    Image.fromarray(recovered_final_array).save(output_path_recovered)
    print(f"Recovered image saved to: {output_path_recovered}")

    # --- 5. 验证 ---
    print("\n--- Verification ---")
    is_match = (np.array(watermark_bits) == np.array(extracted_bits)).all()
    print(f"Is extracted watermark identical to original? {is_match}")

    diff = np.sum(np.abs(image_uint8.astype(np.float64) - recovered_final_array.astype(np.float64)))
    print(f"Is recovered image identical to original? {diff == 0.0}")
    print(f"Total pixel difference (L1 norm): {diff}")

def embed_on_canvas(crmark, canvas_array, watermark_bits):
    h, w, _ = canvas_array.shape
    patch_size = crmark.img_size
    bits_per_patch = crmark.bit_length
    
    watermark_cursor = 0
    stego_canvas = canvas_array.copy()

    for i in tqdm(range(h // patch_size), desc="Encoding Canvas"):
        for j in range(w // patch_size):
            patch = canvas_array[i*patch_size:(i+1)*patch_size, j*patch_size:(j+1)*patch_size, :]
            chunk = watermark_bits[watermark_cursor : watermark_cursor + bits_per_patch]
            
            success, stego_pil = crmark.encode_bits(patch, chunk)
            if not success: return False, None
            
            stego_canvas[i*patch_size:(i+1)*patch_size, j*patch_size:(j+1)*patch_size, :] = np.array(stego_pil)
            watermark_cursor += bits_per_patch
            
    return True, stego_canvas

def recover_from_canvas(crmark, stego_canvas_array):
    h, w, _ = stego_canvas_array.shape
    patch_size = crmark.img_size
    
    recovered_canvas = stego_canvas_array.copy()
    extracted_bits = []

    for i in tqdm(range(h // patch_size), desc="Recovering Canvas"):
        for j in range(w // patch_size):
            patch = stego_canvas_array[i*patch_size:(i+1)*patch_size, j*patch_size:(j+1)*patch_size, :]
            
            is_attacked, cover_pil, rec_bits = crmark.recover_bits(patch)
            if cover_pil is None: return False, None, None

            recovered_canvas[i*patch_size:(i+1)*patch_size, j*patch_size:(j+1)*patch_size, :] = np.array(cover_pil)
            if rec_bits: extracted_bits.extend(rec_bits)

    return True, recovered_canvas, extracted_bits


# --- 主程序入口 ---
if __name__ == "__main__":
    large_tiff_path = "images/ceshiyaogantuxiang.tif"
    if not os.path.exists(large_tiff_path):
        exit(f"Error: Real remote sensing image not found at '{large_tiff_path}'.")

    stego_output_path = "output_large/stego_from_real_tiff.png"
    recovered_cover_path = "output_large/recovered_from_real_tiff.png"
    
    print("Initializing CRMark model once...")
    crmark_model = CRMark(model_mode="color_256_64")

    total_watermark_bits = [random.randint(0, 1) for _ in range(200000)]
    
    process_tiff_image_final(
        crmark_instance=crmark_model,
        input_path=large_tiff_path,
        output_path_stego=stego_output_path,
        output_path_recovered=recovered_cover_path,
        watermark_bits=total_watermark_bits,
    )

    