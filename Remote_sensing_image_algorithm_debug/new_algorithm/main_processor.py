# main_processor.py
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
from image_preprocessor import ImagePreprocessor

def process_large_image(
    crmark_instance: CRMark,
    input_path: str,
    output_path: str,
    mode: str = 'encode',
    watermark_bits: list = None,
    watermark_map_path: str = None
):
    """处理大型遥感图像（分块处理）"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 初始化图像预处理器
    preprocessor = ImagePreprocessor()
    
    print(f"Loading large image from: {input_path}")
    large_image = preprocessor.load_image(input_path)
    h, w, c = large_image.shape
    print(f"Image dimensions: {w}x{h}, Channels: {c}")
    
    patch_size = crmark_instance.img_size
    bits_per_patch = crmark_instance.bit_length

    # 计算分块数量
    patches_x = math.ceil(w / patch_size)
    patches_y = math.ceil(h / patch_size)
    total_patches = patches_x * patches_y
    print(f"Image will be divided into {patches_y}x{patches_x} = {total_patches} patches.")
    
    # 创建输出画布
    output_canvas = np.zeros((h, w, c), dtype=np.uint8)
    
    watermark_cursor = 0
    watermark_map = []
    extracted_bits = []
    successful_patches = 0
    
    # 如果是恢复模式，加载水印地图
    if mode == 'recover' and watermark_map_path and os.path.exists(watermark_map_path):
        with open(watermark_map_path, 'r') as f:
            watermark_map = json.load(f)
    
    # 处理每个分块
    for i in tqdm(range(patches_y), desc=f"Processing rows ({mode})"):
        for j in range(patches_x):
            # 计算当前分块的坐标
            y_start = i * patch_size
            y_end = min((i + 1) * patch_size, h)
            x_start = j * patch_size
            x_end = min((j + 1) * patch_size, w)
            
            # 获取当前分块
            patch = large_image[y_start:y_end, x_start:x_end, :]
            patch_h, patch_w, _ = patch.shape
            
            # 如果分块尺寸不足，进行填充
            if patch_h < patch_size or patch_w < patch_size:
                padded_patch = np.pad(
                    patch, 
                    ((0, patch_size - patch_h), (0, patch_size - patch_w), (0, 0)), 
                    mode='edge'
                )
            else:
                padded_patch = patch
            
            # 处理当前分块
            processed_patch = None
            
            if mode == 'encode':
                # 嵌入水印
                if watermark_bits and watermark_cursor < len(watermark_bits):
                    chunk = watermark_bits[watermark_cursor:watermark_cursor + bits_per_patch]
                    if len(chunk) < bits_per_patch:
                        chunk += [0] * (bits_per_patch - len(chunk))
                    
                    success, stego_pil = crmark_instance.encode_bits(padded_patch, chunk)
                    if success:
                        processed_patch = np.array(stego_pil)
                        watermark_map.append(1)  # 标记成功嵌入
                    else:
                        processed_patch = padded_patch
                        watermark_map.append(0)  # 标记嵌入失败
                    
                    watermark_cursor += bits_per_patch
                else:
                    processed_patch = padded_patch
                    watermark_map.append(0)  # 没有水印可嵌入
            
            elif mode == 'recover':
                # 恢复图像和水印
                if watermark_map and len(watermark_map) > i * patches_x + j and watermark_map[i * patches_x + j] == 1:
                    is_attacked, cover_pil, rec_bits = crmark_instance.recover_bits(padded_patch)
                    if cover_pil is not None:
                        processed_patch = np.array(cover_pil)
                        if rec_bits:
                            extracted_bits.extend(rec_bits)
                        successful_patches += 1
                    else:
                        processed_patch = padded_patch
                else:
                    processed_patch = padded_patch
            
            # 将处理后的分块放回输出画布
            if processed_patch is not None:
                output_canvas[y_start:y_end, x_start:x_end, :] = processed_patch[:patch_h, :patch_w, :]
    
    # 保存输出图像
    Image.fromarray(output_canvas).save(output_path)
    print(f"Processing complete. Image saved to: {output_path}")
    
    # 保存水印地图（如果是嵌入模式）
    if mode == 'encode' and watermark_map_path:
        with open(watermark_map_path, 'w') as f:
            json.dump(watermark_map, f)
        successful_embeddings = sum(watermark_map)
        print(f"Total successful embeddings: {successful_embeddings}/{total_patches}")
        return successful_embeddings * bits_per_patch
    
    # 返回提取的水印（如果是恢复模式）
    if mode == 'recover':
        return extracted_bits

def test_jpeg_robustness(input_path: str, watermark_str: str):
    """测试JPEG压缩后的鲁棒性"""
    print("\n\n--- Testing JPEG Robustness ---")
    
    # 初始化CRMark
    crmark = CRMark(model_mode="color_256_64")
    
    # 加载图像
    preprocessor = ImagePreprocessor()
    cover_img = preprocessor.load_image(input_path)
    
    # 1. 嵌入水印
    print(f"Encoding message '{watermark_str}' into the image...")
    success, stego_pil = crmark.encode(cover_img, watermark_str)
    if not success:
        print("JPEG Test: Encoding failed.")
        return
    
    # 2. 保存为JPEG格式
    jpeg_path = "output_large/stego_image.jpg"
    stego_pil.save(jpeg_path, quality=95)
    print(f"Stego image saved as JPEG: {jpeg_path}")
    
    # 3. 加载JPEG图像
    jpeg_stego_array = np.array(Image.open(jpeg_path))
    
    # 4. 提取水印
    print("Attempting to extract watermark from JPEG file...")
    is_decoded, extracted_message = crmark.decode(jpeg_stego_array)
    
    # 5. 验证结果
    print("\n--- JPEG Test Results ---")
    print(f"Original message:    '{watermark_str}'")
    print(f"Extracted message:   '{extracted_message}'")
    print(f"Successfully decoded: {is_decoded}")
    print(f"Match:               {watermark_str == extracted_message}")

def full_script():
    """完整的测试脚本"""
    # 确保输出目录存在
    os.makedirs("output_large", exist_ok=True)
    
    # 测试图像路径
    large_cover_path = "images/large_cover.png"
    if not os.path.exists(large_cover_path):
        print(f"Error: Test image not found at '{large_cover_path}'")
        return
    
    # 1. 无损可逆测试 (PNG)
    print("\n" + "="*60)
    print("   PNG Reversible Test")
    print("="*60)
    
    stego_output_path = "output_large/stego_image.png"
    recovered_cover_path = "output_large/recovered_cover.png"
    wm_map_path = "output_large/watermark_map.json"
    
    # 初始化CRMark
    crmark = CRMark(model_mode="color_256_64")
    
    # 生成水印数据
    total_watermark_bits = [random.randint(0, 1) for _ in range(100000)]
    
    # 嵌入水印
    print("\n--- Embedding Watermark ---")
    bits_embedded = process_large_image(
        crmark_instance=crmark,
        input_path=large_cover_path,
        output_path=stego_output_path,
        watermark_bits=total_watermark_bits,
        mode='encode',
        watermark_map_path=wm_map_path
    )
    
    print(f"Total bits embedded: {bits_embedded}")
    
    # 恢复图像和水印
    print("\n--- Recovering Image and Watermark ---")
    extracted_bits = process_large_image(
        crmark_instance=crmark,
        input_path=stego_output_path,
        output_path=recovered_cover_path,
        mode='recover',
        watermark_map_path=wm_map_path
    )
    
    # 验证结果
    print("\n--- Verification ---")
    original_embedded = total_watermark_bits[:bits_embedded]
    print(f"Bits embedded: {len(original_embedded)}")
    print(f"Bits extracted: {len(extracted_bits)}")
    
    if len(original_embedded) == len(extracted_bits):
        match_count = sum(1 for a, b in zip(original_embedded, extracted_bits) if a == b)
        accuracy = match_count / len(original_embedded) * 100
        print(f"Accuracy: {accuracy:.2f}%")
    else:
        print("Watermark length mismatch")
    
    # 2. JPEG鲁棒性测试
    test_jpeg_robustness(input_path=large_cover_path, watermark_str="hello")

if __name__ == "__main__":
    print("--- EXECUTING main_processor.py ---")
    full_script()
    print("\n✓ All tests completed.")