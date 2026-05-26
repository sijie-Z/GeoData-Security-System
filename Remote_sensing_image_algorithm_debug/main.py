# # import os
# # import numpy as np
# # from PIL import Image
# # from crmark import CRMark

# # # --- 1. 初始化 ---
# # print("Initializing CRMark... (If it's the first time, it will download the model)")
# # # 使用 256x256 彩色模型，可嵌入5个字符（或等效的40比特+BCH码）
# # crmark = CRMark(model_mode="color_256_64") 
# # os.makedirs("output", exist_ok=True) # 创建输出文件夹

# # # --- 2. 准备数据 ---
# # cover_path = "images/cover.jpg"
# # cover_image = Image.open(cover_path).convert("RGB").resize((256, 256))
# # cover_array = np.array(cover_image)

# # # 您的审批信息
# # message_to_embed = '{"app":"Alice","rev":"Bob"}' # 假设这是您的信息

# # # 将信息转为QR码比特流 (以备后用)
# # # 这里我们先用简单的字符串接口做测试
# # str_to_embed = "hello" # 注意：color_256_64模型要求字符串长度为5

# # # --- 3. 嵌入水印 ---
# # print(f"\nEmbedding message: '{str_to_embed}' into {cover_path}")
# # success, stego_image_pil = crmark.encode(cover_array, str_to_embed)

# # if not success:
# #     print("Embedding failed!")
# # else:
# #     stego_path = "output/stego_image.jpg"
# #     stego_image_pil.save(stego_path)
# #     print(f"Embedding successful. Stego image saved to: {stego_path}")

# #     # --- 4. 从无损图像中恢复 ---
# #     print("\n--- Testing Recovery from a CLEAN image ---")
# #     stego_array_clean = np.array(Image.open(stego_path))
    
# #     is_attacked, rec_cover_pil, rec_message = crmark.recover(stego_array_clean)
    
# #     if rec_cover_pil:
# #         rec_cover_path = "output/recovered_cover.jpg"
# #         rec_cover_pil.save(rec_cover_path)
        
# #         # 验证恢复
# #         rec_cover_array = np.array(rec_cover_pil)
# #         diff = np.sum(np.abs(cover_array.astype(float) - rec_cover_array.astype(float)))
        
# #         print(f"Recovered message: '{rec_message}'")
# #         print(f"Was image attacked? {is_attacked}")
# #         print(f"Is recovered cover identical to original? {diff == 0.0}")
# #         print(f"Recovered cover image saved to: {rec_cover_path}")
# #     else:
# #         print("Recovery failed.")




# import os
# import numpy as np
# from PIL import Image
# from crmark import CRMark
# import math

# # --- Phase 1: Tiling-based Encoding ---
# def encode_large_image(image_path: str, watermark_bits: list, patch_size: int = 256):
#     print(f"Loading large image from {image_path}...")
#     large_image = Image.open(image_path).convert("RGB")
#     w, h = large_image.size
    
#     # 创建一个空的numpy数组来存放最终的带水印图像
#     stego_large_array = np.zeros_like(np.array(large_image))
    
#     # 计算需要多少个图块
#     patches_x = math.ceil(w / patch_size)
#     patches_y = math.ceil(h / patch_size)
#     total_patches = patches_x * patches_y
    
#     # 将水印比特流分块
#     bits_per_patch = math.ceil(len(watermark_bits) / total_patches)
    
#     crmark = CRMark(model_mode="color_256_64")
#     # 注意: color_256_64 模型的水印容量是固定的 (约40个净比特)。
#     # 如果您的bits_per_patch超过这个容量，就需要用更大容量的模型或多次嵌入。
#     # 此处为简化示例，假设容量足够。你需要使用 encode_bits。
#     # 实际使用中，你需要检查 len(watermark_chunk) 是否小于 crmark.bit_length。
    
#     bit_cursor = 0
#     for i in range(patches_y):
#         for j in range(patches_x):
#             # 定义当前图块的坐标
#             box = (j * patch_size, i * patch_size, (j + 1) * patch_size, (i + 1) * patch_size)
            
#             # 裁剪图块
#             patch = large_image.crop(box)
            
#             # 如果图块尺寸不对，需要填充到patch_size
#             if patch.size != (patch_size, patch_size):
#                 patch = Image.fromarray(np.pad(np.array(patch), 
#                                  ((0, patch_size - patch.height), (0, patch_size - patch.width), (0, 0)), 
#                                  'constant', constant_values=0))

#             patch_array = np.array(patch)
            
#             # 获取当前图块需要嵌入的水印
#             watermark_chunk = watermark_bits[bit_cursor : bit_cursor + bits_per_patch]
#             if not watermark_chunk: # 如果水印用完了就跳出
#                 stego_large_array[box[1]:box[3], box[0]:box[2], :] = patch_array[:h-i*patch_size, :w-j*patch_size, :]
#                 continue
            
#             # --- 核心嵌入步骤 ---
#             # 为了演示，我们先用固定长度的随机比特流
#             # 实际中应传入 watermark_chunk 并处理长度问题
#             dummy_watermark_for_patch = [random.randint(0, 1) for _ in range(crmark.bit_length)] 
#             success, stego_patch_pil = crmark.encode_bits(patch_array, dummy_watermark_for_patch)
            
#             if success:
#                 stego_patch_array = np.array(stego_patch_pil)
#                 # 将处理后的图块放回大图中对应的位置
#                 final_h = min(patch_size, h - i * patch_size)
#                 final_w = min(patch_size, w - j * patch_size)
#                 stego_large_array[box[1]:box[1]+final_h, box[0]:box[0]+final_w, :] = stego_patch_array[:final_h, :final_w, :]
#             else:
#                 print(f"Warning: Embedding failed for patch ({i}, {j})")
#                 # 如果失败，就放回原图块
#                 stego_large_array[box[1]:box[3], box[0]:box[2], :] = patch_array[:h-i*patch_size, :w-j*patch_size, :]

#             bit_cursor += bits_per_patch
#             print(f"Processed patch ({i+1}/{patches_y}, {j+1}/{patches_x})")
            
#     return Image.fromarray(stego_large_array)

# # --- 使用示例 ---
# # 假设你有一个大的遥感影像
# # large_image_path = "path/to/your/large_remote_sensing_image.tif"
# # dummy_large_image = Image.fromarray(np.random.randint(0, 255, (800, 1000, 3), dtype=np.uint8))
# # dummy_large_image.save("images/large_cover.png")
# large_image_path = "images/large_cover.png"

# # 和一个长的QR码比特流
# # my_qr_bits = [...] 
# my_qr_bits = [random.randint(0,1) for _ in range(1000)] # 假设有1000比特

# # 调用分块嵌入函数
# final_stego_image = encode_large_image(large_image_path, my_qr_bits)
# final_stego_image.save("output/large_stego_image.png")
# print("\nLarge image processing finished!")



import os
import numpy as np
from PIL import Image
from crmark import CRMark

# --- 1. 初始化 ---
print("Initializing CRMark... (If it's the first time, it will download the model)")
crmark = CRMark(model_mode="color_256_64") 
os.makedirs("output", exist_ok=True)

# --- 2. 准备数据 ---
# 修改这里，确保你的输入文件名正确
cover_path = "images/cover1.png" # 强烈建议输入也使用PNG
stego_path = "output/stego_image.png" # 输出必须是PNG
rec_cover_path = "output/recovered_cover1.png" # 输出也必须是PNG

# 加载图像并确保是RGB格式，然后缩放到模型所需尺寸
cover_image = Image.open(cover_path).convert("RGB").resize((256, 256))
cover_array = np.array(cover_image)

# 使用一个长度为5的字符串进行测试
str_to_embed = "hello" 

# --- 3. 嵌入水印 ---
print(f"\nEmbedding message: '{str_to_embed}' into {cover_path}")
success, stego_image_pil = crmark.encode(cover_array, str_to_embed)

if not success:
    print("Embedding failed!")
else:
    # 保存为PNG格式
    stego_image_pil.save(stego_path)
    print(f"Embedding successful. Stego image saved to: {stego_path}")

    # --- 4. 从无损图像中恢复 ---
    print("\n--- Testing Recovery from a CLEAN image ---")
    # 从PNG文件加载
    stego_array_clean = np.array(Image.open(stego_path))
    
    # 传入Numpy数组进行恢复
    is_attacked, rec_cover_pil, rec_message = crmark.recover(stego_array_clean)
    
    if rec_cover_pil:
        # 保存恢复出的图像
        rec_cover_pil.save(rec_cover_path)
        
        # 验证恢复结果
        rec_cover_array = np.array(rec_cover_pil)
        # 计算原始图像和恢复图像的像素值绝对差之和
        diff = np.sum(np.abs(cover_array.astype(np.float64) - rec_cover_array.astype(np.float64)))
        
        print(f"Recovered message: '{rec_message}'")
        print(f"Was image attacked? {is_attacked}")
        # 如果差值为0，说明完美恢复
        print(f"Is recovered cover identical to original? {diff == 0.0}") 
        print(f"Total pixel difference (L1 norm): {diff}")
        print(f"Recovered cover image saved to: {rec_cover_path}")
    else:
        print("Recovery failed.")