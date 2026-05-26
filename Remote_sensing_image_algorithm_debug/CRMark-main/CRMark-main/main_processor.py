# =======================================================
#               MAIN PROCESSOR SCRIPT
# =======================================================
print("--- EXECUTING main_processor.py ---")

import os
import math
import numpy as np
from PIL import Image
from crmark import CRMark
import random
import imageio.v2 as imageio # 引入新库，为遥感做准备

# --- 核心功能函数 ---
def process_large_image(
    input_path: str,
    output_path: str,
    watermark_bits: list,
    mode: str = 'encode'
):
    # (这部分代码和之前成功的 final_run.py 完全一样，此处省略以保持简洁)
    # ... 您可以从之前的邮件中复制这整个函数，或者直接使用下面的完整脚本 ...
    # 为了保证完整性，我将在下面提供完整的脚本

# --- 新增功能：测试JPEG鲁棒性 ---
    def test_jpeg_robustness(input_path: str, watermark_str: str):
        print("\n\n--- Testing JPEG Robustness ---")
    
    crmark = CRMark(model_mode="color_256_64")
    
    # 1. 准备一张256x256的图
    cover_image = Image.open(input_path).convert("RGB").resize((256, 256))
    cover_array = np.array(cover_image)
    
    # 2. 嵌入字符串水印
    print(f"Encoding message '{watermark_str}' into the image...")
    success, stego_pil = crmark.encode(cover_array, watermark_str)
    if not success:
        print("JPEG Test: Encoding failed.")
        return

    # 3. 【关键】保存为有损的JPEG格式
    jpeg_path = "output_large/stego_image.jpg"
    stego_pil.save(jpeg_path, quality=95) # quality=95 是高质量JPEG
    print(f"Stego image saved as a lossy JPEG: {jpeg_path}")
    
    # 4. 加载被JPEG压缩过的图像
    jpeg_stego_array = np.array(Image.open(jpeg_path))
    
    # 5. 【关键】调用 decode (鲁棒提取)，而不是 recover (完美恢复)
    print("Attempting to robustly DECODE watermark from the JPEG file...")
    is_decoded, extracted_message = crmark.decode(jpeg_stego_array)
    
    # 6. 验证结果
    print("\n--- JPEG Test Verification ---")
    print(f"Was watermark successfully decoded? {is_decoded}")
    print(f"Original message:    '{watermark_str}'")
    print(f"Extracted message:   '{extracted_message}'")
    print(f"Is message correct?  {watermark_str == extracted_message}")
    
    # 7. (可选) 尝试用 recover，看看会发生什么
    print("\n(Optional) Attempting to RECOVER from the JPEG file (expected to fail)...")
    is_attacked, rec_cover_pil, _ = crmark.recover(jpeg_stego_array)
    if not is_attacked and rec_cover_pil is not None:
         diff = np.sum(np.abs(cover_array.astype(np.float64) - np.array(rec_cover_pil).astype(np.float64)))
         print(f"Recover reported image was NOT attacked. Pixel difference: {diff}. (This is unexpected for JPEG)")
    else:
         print("Recover correctly reported that the image was attacked or recovery failed.")

# --- 完整脚本 ---
def full_script():
    # 复制之前 final_run.py 的完整 process_large_image 函数
    def process_large_image(input_path: str, output_path: str, watermark_bits: list, mode: str = 'encode'):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        patch_size = 256
        crmark = CRMark(model_mode="color_256_64")
        bits_per_patch = crmark.bit_length
        print(f"Loading large image from: {input_path}")
        large_image = Image.open(input_path).convert("RGB")
        w, h = large_image.size
        output_large_array = np.array(large_image).copy()
        patches_x = math.ceil(w / patch_size)
        patches_y = math.ceil(h / patch_size)
        total_patches = patches_x * patches_y
        print(f"Image will be divided into {patches_y}x{patches_x} = {total_patches} patches.")
        watermark_cursor = 0
        extracted_bits = []
        processed_patches_count = 0
        for i in range(patches_y):
            for j in range(patches_x):
                left = j * patch_size
                upper = i * patch_size
                right = min((j + 1) * patch_size, w)
                lower = min((i + 1) * patch_size, h)
                patch_pil = large_image.crop((left, upper, right, lower))
                original_w, original_h = patch_pil.size
                if original_h == patch_size and original_w == patch_size:
                    processed_patches_count += 1
                    patch_array = np.array(patch_pil)
                    processed_patch_array = None
                    if mode == 'encode':
                        chunk_to_embed = watermark_bits[watermark_cursor : watermark_cursor + bits_per_patch]
                        if len(chunk_to_embed) > 0:
                            if len(chunk_to_embed) < bits_per_patch: chunk_to_embed.extend([0] * (bits_per_patch - len(chunk_to_embed)))
                            success, stego_pil = crmark.encode_bits(patch_array, chunk_to_embed)
                            if success: processed_patch_array = np.array(stego_pil)
                        watermark_cursor += bits_per_patch
                    elif mode == 'recover':
                        patch_array = np.array(patch_pil)
                        is_attacked, cover_pil, rec_bits = crmark.recover_bits(patch_array)
                        if cover_pil is not None:
                            processed_patch_array = np.array(cover_pil)
                            if rec_bits: extracted_bits.extend(rec_bits)
                    if processed_patch_array is not None:
                        output_large_array[upper:lower, left:right, :] = processed_patch_array
                    print(f"Processed patch ({i*patches_x + j + 1}/{total_patches}) - Full size -> Success")
                else:
                    print(f"Skipping edge patch ({i*patches_x + j + 1}/{total_patches}) - Size: ({original_h}, {original_w})")
                    continue
        output_image_pil = Image.fromarray(output_large_array)
        output_image_pil.save(output_path)
        print(f"\nProcessing complete. Total patches processed for watermarking: {processed_patches_count}/{total_patches}")
        print(f"Image saved to: {output_path}")
        if mode == 'recover':
            return output_image_pil, extracted_bits
        else:
            return True, watermark_cursor

    # --- 主程序 ---
    large_cover_path = "images/large_cover.png"
    if not os.path.exists(large_cover_path):
        exit(f"Error: Test image not found at '{large_cover_path}'")

    # 1. 执行我们已经成功的PNG无损可逆测试
    stego_output_path = "output_large/final_stego_image.png"
    recovered_cover_path = "output_large/final_recovered_cover.png"
    total_watermark_bits = [random.randint(0, 1) for _ in range(100000)]
    print("\n--- Starting PNG Reversible Test ---")
    _, bits_embedded = process_large_image(input_path=large_cover_path, output_path=stego_output_path, watermark_bits=total_watermark_bits, mode='encode')
    _, extracted_watermark = process_large_image(input_path=stego_output_path, output_path=recovered_cover_path, watermark_bits=[], mode='recover')
    print("\n--- PNG Test Verification ---")
    original_embedded_part = total_watermark_bits[:bits_embedded]
    is_match = (np.array(original_embedded_part) == np.array(extracted_watermark)).all()
    print(f"Is extracted watermark identical to original? {is_match}")
    original_large_array = np.array(Image.open(large_cover_path).convert("RGB"))
    recovered_large_array = np.array(Image.open(recovered_cover_path))
    diff = np.sum(np.abs(original_large_array.astype(np.float64) - recovered_large_array.astype(np.float64)))
    print(f"Is recovered large image identical to original? {diff == 0.0}")

    # 2. 执行新增的JPEG鲁棒性测试
    test_jpeg_robustness(input_path=large_cover_path, watermark_str="hello")

if __name__ == "__main__":
    full_script()