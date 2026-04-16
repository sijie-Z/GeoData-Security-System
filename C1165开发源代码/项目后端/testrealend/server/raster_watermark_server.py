
import os
import cv2
from datetime import datetime
from extension.extension import db
import logging
from flask import current_app
import numpy as np
import base64

# 使用绝对导入，确保无论从何处运行，都能正确找到模块
from algorithm.raster_preprocessor import load_as_rgb_array
# 将导入文件名更改为 raster_embed_lsb
from algorithm.raster_embed_lsb import embed as embed_engine
# 将导入文件名更改为 raster_extract_lsb
from algorithm.raster_extract_lsb import extract as extract_engine

from model.Application import Application
from model.Raster_Data import RasterData
from model.Embed_File_Record import EmbedFileRecord 

class RasterWatermarkServer:
    """
    栅格水印处理服务类。
    包含了嵌入和提取水印的静态方法。
    """
    
    @staticmethod
    def embed_watermark(application_id: int) -> dict:
        """
        根据申请ID嵌入水印。
        
        Args:
            application_id (int): 待处理的申请ID。
        
        Returns:
            dict: 包含处理结果的字典，如成功状态、消息和生成文件的路径。
        """
        try:
            embed_dir = current_app.config.get('EMBED_FOLDER', 'embed')
            
            # 从数据库查询申请记录和对应的栅格数据
            app = db.session.query(Application).filter_by(id=application_id).first()
            if not app or not app.QRcode:
                return {"success": False, "message": "申请记录或QR码不存在"}

            host_image = db.session.query(RasterData).filter_by(id=app.data_id).first()
            if not host_image:
                return {"success": False, "message": "找不到对应的栅格数据"}

            host_path = host_image.file_path
            
            # 直接从数据库的二进制数据加载QR码
            watermark_bytes = np.frombuffer(app.QRcode, np.uint8)
            watermark_bgr_from_db = cv2.imdecode(watermark_bytes, cv2.IMREAD_COLOR)

            output_filename = f"stego_raster_app_{application_id}.png"
            output_path = os.path.join(embed_dir, "raster", output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 加载并转换宿主图像
            host_array_rgb = load_as_rgb_array(host_path)
            host_bgr = cv2.cvtColor(host_array_rgb, cv2.COLOR_RGB2BGR)
            
            # 调用水印嵌入算法
            stego_bgr = embed_engine(host_bgr, watermark_bgr_from_db)
            
            # 保存嵌入水印后的图像
            cv2.imwrite(output_path, stego_bgr)
            
            # 更新或创建嵌入文件记录
            embed_record = EmbedFileRecord.query.filter_by(application_id=application_id).first()
            if not embed_record:
                embed_record = EmbedFileRecord(application_id=application_id, data_id=app.data_id)
            
            embed_record.embed_person = app.adm2_name
            embed_record.applicant = app.applicant_name
            embed_record.generate_filename = output_filename
            embed_record.generate_file_path = output_path
            embed_record.embed_time = datetime.utcnow()
            
            db.session.add(embed_record)
            db.session.commit()
            
            logging.info(f"申请ID {application_id} 的栅格水印嵌入成功。")
            return {"success": True, "stego_path": output_path, "filename": output_filename}

        except Exception as e:
            db.session.rollback()
            logging.error(f"处理申请ID {application_id} 嵌入时出错: {e}")
            return {"success": False, "message": f"服务器内部错误: {e}"}

    @staticmethod
    def extract_watermark(stego_path: str, application_id: int) -> dict:
        """
        从带有水印的图像中提取水印。
        
        Args:
            stego_path (str): 带有水印的图像文件路径。
            application_id (int): 关联的申请ID。
        
        Returns:
            dict: 包含处理结果的字典，如成功状态和提取出的水印二进制数据。
        """
        try:
            extracted_dir = os.path.join(current_app.config.get('EXTRACTED_FOLDER', 'extracted'), 'raster')

            # 获取原始QR码的尺寸信息
            app = db.session.query(Application).filter_by(id=application_id).first()
            if not app or not app.QRcode:
                return {"success": False, "message": "找不到关联的申请记录或原始QR码"}
            
            watermark_bytes = np.frombuffer(app.QRcode, np.uint8)
            watermark_img_for_size = cv2.imdecode(watermark_bytes, cv2.IMREAD_COLOR)
            h_wm, w_wm, _ = watermark_img_for_size.shape

            # 加载带有水印的图像
            stego_array_rgb = load_as_rgb_array(stego_path)
            stego_bgr = cv2.cvtColor(stego_array_rgb, cv2.COLOR_RGB2BGR)

            # 调用水印提取算法
            extracted_bgr = extract_engine(stego_bgr, h_wm, w_wm)
            
            # 保存提取出的水印图像
            output_filename = f"extracted_raster_from_app_{application_id}.png"
            output_path = os.path.join(extracted_dir, output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cv2.imwrite(output_path, extracted_bgr)
            
            # 读取提取出的水印图像为二进制数据
            with open(output_path, "rb") as image_file:
                extracted_binary = image_file.read()

            logging.info(f"从申请ID {application_id} 的文件中成功提取水印。")
            return {"success": True, "extracted_binary": extracted_binary}

        except Exception as e:
            logging.error(f"处理申请ID {application_id} 提取时出错: {e}")
            return {"success": False, "message": f"服务器内部错误: {e}"}
