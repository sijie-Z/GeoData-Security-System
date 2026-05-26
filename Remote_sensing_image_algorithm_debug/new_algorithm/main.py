import os
import numpy as np
from PIL import Image
from image_preprocessor import ImagePreprocessor
from crmark import CRMark
import random
import traceback

def main():
    # 创建输出目录
    os.makedirs("output", exist_ok=True)
    
    # 初始化图像预处理器
    preprocessor = ImagePreprocessor()
    
    # 测试用例
    test_cases = [
        {
            "name": "Color Image (256x256)",
            "image_path": "images/color_cover.png",
            "model_mode": "color_256_64",
            "message": "hello"
        },
        {
            "name": "Grayscale Image (512x512)",
            "image_path": "images/gray_cover.png",
            "model_mode": "gray_512_256",
            "message": "CRMark: Hide&Recover"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {test_case['name']}")
        print(f"{'='*60}")
        
        try:
            # 加载和预处理图像
            print(f"Loading image: {test_case['image_path']}")
            cover_img = preprocessor.load_image(test_case["image_path"])
            
            # 初始化CRMark
            print(f"Initializing CRMark model: {test_case['model_mode']}")
            crmark = CRMark(model_mode=test_case["model_mode"])
            print("Model initialized successfully")
            
            # 嵌入水印
            print(f"\nEmbedding message: '{test_case['message']}'")
            success, stego_image = crmark.encode(cover_img, test_case["message"])
            
            if not success:
                print("Embedding failed!")
                continue
            
            # 保存隐写图像
            stego_path = f"output/stego_{test_case['model_mode']}.png"
            stego_image.save(stego_path)
            print(f"Stego image saved to: {stego_path}")
            
            # 恢复图像和水印
            print("\nRecovering original image and watermark...")
            is_attacked, recovered_image, recovered_message = crmark.recover(np.array(stego_image))
            
            if is_attacked:
                print("Warning: Image may have been tampered with!")
            
            if recovered_image:
                # 保存恢复的图像
                recovered_path = f"output/recovered_{test_case['model_mode']}.png"
                recovered_image.save(recovered_path)
                print(f"Recovered image saved to: {recovered_path}")
                
                # 计算PSNR
                cover_img_pil = Image.fromarray(cover_img)
                recovered_img_pil = recovered_image
                
                # 转换为numpy数组计算PSNR
                cover_np = np.array(cover_img_pil).astype(np.float32)
                recovered_np = np.array(recovered_img_pil).astype(np.float32)
                
                mse = np.mean((cover_np - recovered_np) ** 2)
                if mse == 0:
                    psnr = float('inf')
                else:
                    psnr = 20 * np.log10(255.0 / np.sqrt(mse))
                
                print(f"PSNR between original and recovered: {psnr:.2f} dB")
            
            if recovered_message:
                print(f"Recovered message: '{recovered_message}'")
                print(f"Original message:  '{test_case['message']}'")
                print(f"Match: {recovered_message == test_case['message']}")
        
        except Exception as e:
            print(f"Error processing test case: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    # 检查测试图像是否存在，如果不存在则创建
    if not os.path.exists("images/color_cover.png") or not os.path.exists("images/gray_cover.png"):
        print("Test images not found, creating...")
        from create_test_images import create_test_images
        create_test_images()
    
    main()
    print("\n✓ All tests completed.")