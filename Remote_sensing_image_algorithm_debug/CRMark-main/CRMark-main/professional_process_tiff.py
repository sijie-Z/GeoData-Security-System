# =======================================================
#               PROFESSIONAL TIFF PROCESSING SCRIPT (Industrial Robustness)
# =======================================================
print("--- EXECUTING professional_process_tiff.py (Industrial Robustness) ---")

import os
import math
import numpy as np
from PIL import Image
from crmark import CRMark
import random
import imageio.v2 as imageio
import gc
from tqdm import tqdm
import json

def process_tiff_image(
    crmark_instance: CRMark,
    input_path: str,
    output_path: str,
    watermark_bits: list,
    mode: str = 'encode',
    watermark_map_path: str = None
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    patch_size = 256
    bits_per_patch = crmark_instance.bit_length

    print(f"Loading large image from: {input_path}")
    # 使用 imageio.mimread 来处理可能的多页TIFF
    try:
        large_image_raw = imageio.imread(input_path)
    except Exception as e:
        print(f"Standard imread failed: {e}. Trying with plugin 'tifffile'.")
        large_image_raw = imageio.imread(input_path, plugin='tifffile')
        
    print(f"Original image properties: Shape={large_image_raw.shape}, DataType={large_image_raw.dtype}")

    # --- 数据预处理 ---
    if large_image_raw.dtype == 'uint16':
        large_image_float = large_image_raw.astype(np.float32) / 65535.0
    elif large_image_raw.dtype == 'uint8':
        large_image_float = large_image_raw.astype(np.float32) / 255.0
    elif 'float' in str(large_image_raw.dtype):
        min_val, max_val = np.percentile(large_image_raw, [2, 98])
        large_image_raw = np.clip(large_image_raw, min_val, max_val)
        large_image_float = (large_image_raw - min_val) / (max_val - min_val) if (max_val - min_val) > 0 else np.zeros_like(large_image_raw, dtype=np.float32)
    else:
        raise ValueError(f"Unsupported TIFF data type: {large_image_raw.dtype}")
    
    large_image_uint8 = (large_image_float * 255).astype(np.uint8)
    del large_image_float, large_image_raw
    gc.collect()

    if large_image_uint8.ndim == 2:
        large_image_uint8 = np.stack([large_image_uint8]*3, axis=-1)
    elif large_image_uint8.ndim == 3 and large_image_uint8.shape[2] > 3:
        band_indices = [3, 2, 1] 
        large_image_uint8 = large_image_uint8[:, :, band_indices]
    
    large_image = Image.fromarray(large_image_uint8)
    w, h = large_image.size
    
    output_large_array = np.array(large_image)
    
    patches_x = math.ceil(w / patch_size)
    patches_y = math.ceil(h / patch_size)
    total_patches = patches_x * patches_y
    print(f"Image will be divided into {patches_y}x{patches_x} = {total_patches} patches.")

    watermark_cursor = 0
    extracted_bits = []
    
    watermark_map = []
    if mode == 'recover':
        print(f"Loading watermark map from: {watermark_map_path}")
        with open(watermark_map_path, 'r') as f:
            watermark_map = json.load(f)

    for i in tqdm(range(patches_y), desc=f"Processing Rows for {mode}"):
        for j in range(patches_x):
            patch_index = i * patches_x + j
            left, upper = j * patch_size, i * patch_size
            right, lower = min((j + 1) * patch_size, w), min((i + 1) * patch_size, h)
            
            patch_pil = large_image.crop((left, upper, right, lower))
            original_w, original_h = patch_pil.size
            
            patch_array = np.array(patch_pil)
            pad_h = patch_size - original_h
            pad_w = patch_size - original_w
            if pad_h > 0 or pad_w > 0:
                patch_array = np.pad(patch_array, ((0, pad_h), (0, pad_w), (0, 0)), 'edge')
            
            processed_patch_array = None

            if mode == 'encode':
                chunk_to_embed = watermark_bits[watermark_cursor : watermark_cursor + bits_per_patch]
                patch_is_good = False
                if len(chunk_to_embed) > 0:
                    if len(chunk_to_embed) < bits_per_patch: chunk_to_embed.extend([0] * (bits_per_patch - len(chunk_to_embed)))
                    
                    success_encode, stego_pil = crmark_instance.encode_bits(patch_array, chunk_to_embed)
                    
                    # 【【【 核心修正：双重验证机制 】】】
                    if success_encode:
                        # 编码成功后，立即尝试恢复
                        stego_array_check = np.array(stego_pil)
                        is_attacked, cover_pil_check, rec_bits_check = crmark_instance.recover_bits(stego_array_check)
                        # 只有当恢复也成功时，才认为这个图块是好的
                        if cover_pil_check is not None:
                            processed_patch_array = stego_array_check
                            patch_is_good = True
                
                watermark_map.append(1 if patch_is_good else 0)
                watermark_cursor += bits_per_patch

            elif mode == 'recover':
                if watermark_map[patch_index] == 1:
                    is_attacked, cover_pil, rec_bits = crmark_instance.recover_bits(patch_array)
                    if cover_pil is not None:
                        processed_patch_array = np.array(cover_pil)
                        if rec_bits: extracted_bits.extend(rec_bits)

            if processed_patch_array is not None:
                 source_to_paste = processed_patch_array[:original_h, :original_w, :]
                 output_large_array[upper:lower, left:right, :] = source_to_paste

    output_image_pil = Image.fromarray(output_large_array)
    output_image_pil.save(output_path, quality=100)
    print(f"\nProcessing complete. Image saved to: {output_path}")

    if mode == 'encode':
        print(f"Saving watermark map to: {watermark_map_path}")
        with open(watermark_map_path, 'w') as f:
            json.dump(watermark_map, f)
        successful_patches = sum(watermark_map)
        print(f"Total successful embeddings: {successful_patches}/{total_patches}")
        return successful_patches * bits_per_patch

    elif mode == 'recover':
        return output_image_pil, extracted_bits

# --- 主程序入口 ---
if __name__ == "__main__":
    # 确保imageio可以处理TIFF
    try:
        imageio.plugins.tifffile.download()
    except:
        print("Could not download tifffile plugin, might be already present.")

    large_tiff_path = "images/ceshiyaogantuxiang.tif"
    if not os.path.exists(large_tiff_path):
        exit(f"Error: Real remote sensing image not found at '{large_tiff_path}'.")

    stego_output_path = "output_large/stego_from_real_tiff.png"
    recovered_cover_path = "output_large/recovered_from_real_tiff.png"
    wm_map_path = "output_large/watermark_map.json"

    print("Initializing CRMark model once...")
    crmark_model = CRMark(model_mode="color_256_64")

    # --- 嵌入 ---
    total_watermark_bits = [random.randint(0, 1) for _ in range(200000)]
    print("\n--- Starting Encoding Process ---")
    total_bits_embedded = process_tiff_image(
        crmark_instance=crmark_model,
        input_path=large_tiff_path,
        output_path=stego_output_path,
        watermark_bits=total_watermark_bits,
        mode='encode',
        watermark_map_path=wm_map_path
    )
    
    gc.collect()

    # --- 恢复 ---
    print("\n--- Starting Recovery Process ---")
    _, extracted_watermark = process_tiff_image(
        crmark_instance=crmark_model,
        input_path=stego_output_path,
        output_path=recovered_cover_path,
        watermark_bits=[],
        mode='recover',
        watermark_map_path=wm_map_path
    )
    
    # --- 验证 ---
    print("\n--- Verification ---")
    original_embedded_part = total_watermark_bits[:total_bits_embedded]
    extracted_watermark_trimmed = extracted_watermark

    print(f"Bits that should have been embedded: {len(original_embedded_part)}")
    print(f"Bits actually extracted: {len(extracted_watermark_trimmed)}")

    if len(original_embedded_part) == len(extracted_watermark_trimmed) and len(original_embedded_part) > 0:
        is_match = (np.array(original_embedded_part) == np.array(extracted_watermark_trimmed)).all()
        print(f"Is extracted watermark identical to original? {is_match}")
    else:
        print(f"Watermark length mismatch or no watermark embedded. Cannot compare.")

    # 验证图像恢复的 L1 差异
    # 注意：我们只能期望那些成功嵌入的块被完美恢复。
    # 所以这里的 diff 不会是0，但它反映了可逆部分的恢复情况。
    print("\nNote: Pixel difference will not be zero because some patches were not watermarked.")
    original_image_pil = Image.open(large_tiff_path).convert("RGB")
    original_large_array = np.array(original_image_pil)
    recovered_large_array = np.array(Image.open(recovered_cover_path))
    diff = np.sum(np.abs(original_large_array.astype(np.float64) - recovered_large_array.astype(np.float64)))
    print(f"Total pixel difference (L1 norm): {diff}")