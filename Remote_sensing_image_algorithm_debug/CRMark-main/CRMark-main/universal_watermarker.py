# =============================================================================
#           UNIVERSAL, ROBUST, AND CORRECT WATERMARKING PROCESSOR
#
# This script is the definitive, corrected implementation.
# - It handles any-size images (PNG, BMP, 8-bit TIF) for perfect recovery.
# - It handles JPG for robust watermark extraction (image recovery is impossible).
# - It relies on a patched, robust `crmark.py` to prevent crashes.
# =============================================================================
print("--- EXECUTING UNIVERSAL, ROBUST, AND CORRECT PROCESSOR ---")

import os
import math
import numpy as np
from PIL import Image
from crmark import CRMark
import random
from tqdm import tqdm
import json
import imageio.v2 as imageio

def process_large_image(
    crmark_instance: CRMark,
    input_path: str,
    output_path: str,
    mode: str = 'encode',
    watermark_bits: list = None,
    watermark_map_path: str = None
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    patch_size = crmark_instance.img_size
    bits_per_patch = crmark_instance.bit_length

    print(f"\nLoading image: {input_path}")
    # Pillow is best for converting various formats to a standard RGB array
    large_image = Image.open(input_path).convert("RGB")
    w, h = large_image.size
    
    output_canvas = np.array(large_image)
    
    patches_x = math.ceil(w / patch_size)
    patches_y = math.ceil(h / patch_size)
    total_patches = patches_x * patches_y
    print(f"Image divided into {patches_y}x{patches_x} = {total_patches} patches.")

    watermark_cursor = 0
    new_watermark_map = []
    extracted_bits_list = [None] * total_patches
    successful_patches = 0

    watermark_map = []
    if mode in ['recover', 'decode']:
        with open(watermark_map_path, 'r') as f:
            watermark_map = json.load(f)

    for i in tqdm(range(patches_y), desc=f"Processing Rows ({mode})"):
        for j in range(patches_x):
            patch_index = i * patches_x + j
            
            left, upper = j * patch_size, i * patch_size
            right, lower = min((j + 1) * patch_size, w), min((i + 1) * patch_size, h)
            
            original_patch_pil = large_image.crop((left, upper, right, lower))
            original_w, original_h = original_patch_pil.size
            
            input_patch_array = np.array(original_patch_pil)
            if original_h < patch_size or original_w < patch_size:
                input_patch_array = np.pad(input_patch_array, ((0, patch_size - original_h), (0, patch_size - original_w), (0, 0)), 'edge')

            if mode == 'encode':
                chunk_to_embed = watermark_bits[watermark_cursor : watermark_cursor + bits_per_patch]
                success = False
                if len(chunk_to_embed) == bits_per_patch:
                    is_ok, stego_pil = crmark_instance.encode_bits(input_patch_array, chunk_to_embed)
                    if is_ok:
                        stego_array = np.array(stego_pil)
                        output_canvas[upper:lower, left:right, :] = stego_array[:original_h, :original_w, :]
                        success = True
                new_watermark_map.append(1 if success else 0)
                watermark_cursor += bits_per_patch

            elif mode == 'recover':
                if watermark_map[patch_index] == 1:
                    is_attacked, cover_pil, rec_bits = crmark_instance.recover_bits(input_patch_array)
                    if cover_pil is not None and rec_bits is not None:
                        recovered_array = np.array(cover_pil)
                        output_canvas[upper:lower, left:right, :] = recovered_array[:original_h, :original_w, :]
                        extracted_bits_list[patch_index] = rec_bits
                        successful_patches += 1
            
            elif mode == 'decode':
                 if watermark_map[patch_index] == 1:
                    # 【【核心修正】】decode_bits只返回一个值
                    decoded_bits = crmark_instance.decode_bits(input_patch_array)
                    if decoded_bits is not None:
                         extracted_bits_list[patch_index] = decoded_bits
                         successful_patches += 1
    
    file_ext = os.path.splitext(output_path)[1].lower()
    if file_ext in ['.jpg', '.jpeg']:
        Image.fromarray(output_canvas).save(output_path, quality=95)
    else:
        imageio.imwrite(output_path, output_canvas)
        
    print(f"Processing complete. Image saved to: {output_path}")
    
    if mode == 'encode':
        with open(watermark_map_path, 'w') as f: json.dump(new_watermark_map, f)
        successful_patches = sum(new_watermark_map)
        print(f"Total patches successfully embedded: {successful_patches}/{total_patches}")
        return output_canvas, new_watermark_map
    else:
        print(f"Total patches successfully processed: {successful_patches}/{total_patches}")
        final_extracted_bits = [bit for chunk in extracted_bits_list if chunk is not None for bit in chunk]
        return output_canvas, final_extracted_bits

# --- 主程序入口 ---
if __name__ == "__main__":
    # --- 1. 用户配置 ---
    input_image_path = "images/test.png"
    
    # --- 2. 初始化 ---
    print("Initializing CRMark model...")
    crmark_model = CRMark(model_mode="color_256_64")
    
    # --- 3. 准备资源 ---
    if not os.path.exists(input_image_path):
        exit(f"Error: Input image '{input_image_path}' not found.")
    
    img_w, img_h = Image.open(input_image_path).size
    num_patches = math.ceil(img_w / crmark_model.img_size) * math.ceil(img_h / crmark_model.img_size)
    bits_needed = num_patches * crmark_model.bit_length
    watermark_bits = [random.randint(0, 1) for _ in range(bits_needed)]
    
    wm_map_path = "output_large/watermark_map.json"
    
    # ========================================================================
    #  场景一: 无损格式 (PNG, BMP, TIF) 的完美可逆水印
    # ========================================================================
    print("\n" + "="*60)
    print(" " * 15 + "SCENE 1: LOSSLESS FORMAT (e.g., PNG)")
    print("="*60)
    
    stego_lossless_path = "output_large/stego_lossless.tif"
    recovered_lossless_path = "output_large/recovered_lossless.tif"

    # 嵌入
    _, watermark_map = process_large_image(
        crmark_instance=crmark_model, input_path=input_image_path,
        output_path=stego_lossless_path, watermark_bits=watermark_bits, mode='encode',
        watermark_map_path=wm_map_path
    )
    
    # 恢复
    recovered_array, extracted_bits = process_large_image(
        crmark_instance=crmark_model, input_path=stego_lossless_path,
        output_path=recovered_lossless_path, mode='recover',
        watermark_map_path=wm_map_path
    )
    
    # 验证
    print("\n--- Lossless Test Verification ---")
    successful_patches = sum(watermark_map)
    bits_should_be = successful_patches * crmark_model.bit_length
    
    original_embedded_bits = []
    for i, status in enumerate(watermark_map):
        if status == 1:
            start, end = i * crmark_model.bit_length, (i + 1) * crmark_model.bit_length
            original_embedded_bits.extend(watermark_bits[start:end])
            
    print(f"Bits that should have been embedded: {len(original_embedded_bits)}")
    print(f"Bits actually extracted:              {len(extracted_bits)}")

    if len(original_embedded_bits) == len(extracted_bits) and len(original_embedded_bits) > 0:
        is_match = (np.array(original_embedded_bits) == np.array(extracted_bits)).all()
        print(f"-> Is extracted watermark identical? {is_match}")
        
    original_array = np.array(Image.open(input_image_path).convert("RGB"))
    diff = np.sum(np.abs(original_array.astype(np.float64) - recovered_array.astype(np.float64)))
    print(f"-> Is recovered image identical? {diff == 0.0}")
    print(f"-> Total pixel difference (L1 norm): {diff}")

    # ========================================================================
    #  场景二: 有损格式 (JPG) 的鲁棒水印提取
    # ========================================================================
    print("\n" + "="*60)
    print(" " * 15 + "SCENE 2: LOSSY FORMAT (JPG)")
    print("="*60)
    
    stego_lossy_path = "output_large/stego_lossy.jpg"
    print(f"Converting lossless stego image to lossy JPG: {stego_lossy_path}")
    imageio.imwrite(stego_lossy_path, imageio.imread(stego_lossless_path), quality=95)
    
    # 【【关键】】我们不再尝试恢复图像，只调用'decode'模式提取水印
    _, extracted_bits_from_jpg = process_large_image(
        crmark_instance=crmark_model,
        input_path=stego_lossy_path,
        output_path="output_large/recovered_from_jpg_ignored.tif",
        mode='decode',
        watermark_map_path=wm_map_path
    )
    
    print("\n--- Lossy Test Verification ---")
    print(f"Bits that should have been embedded: {len(original_embedded_bits)}")
    print(f"Bits extracted from JPG:             {len(extracted_bits_from_jpg)}")
    
    if len(original_embedded_bits) == len(extracted_bits_from_jpg) and len(original_embedded_bits) > 0:
        is_match_jpg = (np.array(original_embedded_bits) == np.array(extracted_bits_from_jpg)).all()
        print(f"-> Is watermark extracted from JPG correct? {is_match_jpg}")