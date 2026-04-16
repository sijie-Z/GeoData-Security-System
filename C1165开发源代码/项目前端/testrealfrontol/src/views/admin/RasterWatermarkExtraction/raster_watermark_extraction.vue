<template>
    <div class="watermark-extraction-container">
      <h2>栅格数据水印提取与验证</h2>
      <p class="description">
        请上传您疑似泄露的栅格数据文件（zip或tif格式），并输入对应的原始数据编号，以提取并比对水印。
      </p>
  
      <div class="input-and-upload-section">
        <!-- 输入原始数据编号 -->
        <el-input
          v-model="dataIdInput"
          placeholder="请输入原始数据编号"
          style="width: 250px"
          class="data-id-input"
        />
        
        <!-- 文件上传控件 -->
        <el-upload
          class="upload-demo"
          drag
          :action="uploadUrl"
          :multiple="false"
          accept=".zip,.tif"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :data="uploadData"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            拖放文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              仅支持 zip 或 tif 格式文件
            </div>
          </template>
        </el-upload>
      </div>
  
      <!-- 水印比对结果展示区 -->
      <el-card v-if="comparisonResult.isReady" class="comparison-card">
        <template #header>
          <div class="card-header">
            <span>水印比对结果</span>
          </div>
        </template>
  
        <div class="watermark-display-area">
          <!-- 原始水印 -->
          <div class="watermark-item">
            <div class="watermark-label">原始水印</div>
            <el-image
              :src="`data:image/png;base64,${originalWatermarkBase64}`"
              fit="contain"
              class="watermark-image"
            >
              <template #error>
                <div class="image-slot">
                  <span>加载失败</span>
                </div>
              </template>
            </el-image>
          </div>
  
          <!-- 提取水印 -->
          <div class="watermark-item">
            <div class="watermark-label">提取的水印</div>
            <el-image
              :src="`data:image/png;base64,${extractedWatermarkBase64}`"
              fit="contain"
              class="watermark-image"
            >
              <template #error>
                <div class="image-slot">
                  <span>加载失败</span>
                </div>
              </template>
            </el-image>
          </div>
        </div>
        
        <!-- NC值比对结果 -->
        <div class="nc-value-section">
          <div class="nc-value-text">
            <span class="label">归一化相关系数（NC值）：</span>
            <span class="value">{{ comparisonResult.ncValue }}</span>
          </div>
          <div v-if="comparisonResult.isMatch" class="result-message-box success">
            <el-icon><Check /></el-icon> <span>水印匹配，数据为真</span>
          </div>
          <div v-else class="result-message-box danger">
            <el-icon><Warning /></el-icon> <span>水印不匹配，数据可能被篡改或为盗版</span>
          </div>
        </div>
      </el-card>
  
    </div>
  </template>
  
  <script setup>
  import { reactive, ref, watch } from 'vue';
  import { ElMessage, ElMessageBox } from 'element-plus';
  import { UploadFilled, Check, Warning } from '@element-plus/icons-vue';
  import axios from 'axios';
  
  // 假设后端API的根URL，请根据您的实际环境修改
  const basic_url = import.meta.env.VITE_API_URL;
  
  // 数据状态
  const dataIdInput = ref('');
  const extractedWatermarkBase64 = ref('');
  const originalWatermarkBase64 = ref('');
  const comparisonResult = reactive({
    isReady: false,
    isMatch: false,
    ncValue: null,
  });
  
  // 上传URL，调用后端栅格水印提取接口
  const uploadUrl = `${basic_url}/api/raster/extract`;
  
  // 上传时附带的数据
  const uploadData = reactive({
    data_id: dataIdInput,
  });
  
  // 监听输入框变化，更新上传数据
  watch(dataIdInput, (newValue) => {
    uploadData.data_id = newValue;
  });
  
  // 上传文件前的检查
  const beforeUpload = (file) => {
    if (!dataIdInput.value) {
      ElMessage.error('请先输入原始数据编号');
      return false;
    }
    const isZipOrTif = file.name.toLowerCase().endsWith('.zip') || file.name.toLowerCase().endsWith('.tif');
    if (!isZipOrTif) {
      ElMessage.error('上传文件必须是 .zip 或 .tif 格式');
      return false;
    }
    return true;
  };
  
  // 文件上传成功处理
  const handleUploadSuccess = (response, file) => {
    if (response.status) {
      ElMessage.success(`文件 ${file.name} 上传成功，水印提取中...`);
      // 假设后端返回的数据结构包含原始水印、提取水印和NC值
      extractedWatermarkBase64.value = response.extracted_watermark_base64;
      originalWatermarkBase64.value = response.original_watermark_base64;
      comparisonResult.ncValue = response.nc_value;
      comparisonResult.isReady = true;
      
      // 简单判断NC值是否匹配，阈值可根据实际情况调整
      const matchThreshold = 0.95; 
      comparisonResult.isMatch = response.nc_value > matchThreshold;
  
    } else {
      ElMessage.error(response.msg || `文件 ${file.name} 上传成功但水印提取失败`);
      comparisonResult.isReady = false;
    }
  };
  
  // 文件上传失败处理
  const handleUploadError = (err, file) => {
    ElMessage.error(`文件 ${file.name} 上传失败，请检查网络或服务器日志。`);
    console.error("Error during file upload:", err);
    comparisonResult.isReady = false;
  };
  </script>
  
  <style scoped>
  .watermark-extraction-container {
    padding: 20px;
    max-width: 800px;
    margin: 0 auto;
  }
  
  .description {
    margin-bottom: 20px;
    color: #606266;
  }
  
  .input-and-upload-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }
  
  .data-id-input {
    width: 100%;
  }
  
  .upload-demo {
    width: 100%;
  }
  
  .comparison-card {
    margin-top: 30px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  }
  
  .card-header {
    font-size: 18px;
    font-weight: bold;
  }
  
  .watermark-display-area {
    display: flex;
    justify-content: space-around;
    gap: 20px;
    padding: 20px 0;
  }
  
  .watermark-item {
    text-align: center;
    flex-basis: 45%;
  }
  
  .watermark-label {
    font-weight: bold;
    margin-bottom: 10px;
  }
  
  .watermark-image {
    width: 100%;
    max-width: 200px;
    height: auto;
    min-height: 100px;
    border: 1px dashed #dcdfe6;
    border-radius: 4px;
  }
  
  .image-slot {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
  }
  
  .nc-value-section {
    text-align: center;
    margin-top: 20px;
  }
  
  .nc-value-text {
    font-size: 16px;
    margin-bottom: 15px;
  }
  
  .nc-value-text .label {
    color: #606266;
  }
  
  .nc-value-text .value {
    font-weight: bold;
    color: #333;
  }
  
  .result-message-box {
    display: inline-flex;
    align-items: center;
    padding: 10px 20px;
    border-radius: 4px;
    font-weight: bold;
  }
  
  .result-message-box.success {
    background-color: #f0f9eb;
    color: #67c23a;
    border: 1px solid #e1f3d8;
  }
  
  .result-message-box.danger {
    background-color: #fef0f0;
    color: #f56c6c;
    border: 1px solid #fde2e2;
  }
  </style>
  