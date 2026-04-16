<!-- <template>
    <div class="data-upload-container">

      <div class="page-header">
        <h1 class="page-title">数据资源上传</h1>
        <p class="page-description">
          请在此处上传 SHP 格式的地理数据资源。为确保数据一致性，所有文件需打包为 ZIP 压缩文件。
        </p>
      </div>
  

      <el-card class="upload-main-card">
        <el-form
          ref="uploadFormRef"
          :model="form"
          :rules="rules"
          label-width="120px"
          label-position="top"
          class="upload-form"
          size="large"
        >
          <el-row :gutter="40">
            <el-col :span="12">
              <el-form-item label="数据名称" prop="data_alias">
                <el-input
                  v-model="form.data_alias"
                  placeholder="例如：2023年全国省级行政区划"
                  clearable
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
               <el-form-item label="数据分类 (可选)" prop="category">
                  <el-select v-model="form.category" placeholder="请选择或输入数据分类" filterable allow-create>
                    <el-option label="行政区划" value="行政区划"></el-option>
                    <el-option label="水系" value="水系"></el-option>
                    <el-option label="交通网络" value="交通网络"></el-option>
                    <el-option label="兴趣点 (POI)" value="兴趣点 (POI)"></el-option>
                  </el-select>
                </el-form-item>
            </el-col>
          </el-row>
  
          <el-form-item label="数据简介" prop="data_introduction">
            <el-input
              v-model="form.data_introduction"
              type="textarea"
              :rows="4"
              placeholder="请详细描述数据的来源、坐标系、年份、内容摘要等关键信息，便于其他用户理解和使用。"
              show-word-limit
              maxlength="500"
            />
          </el-form-item>
  
          <el-form-item label="上传 SHP 压缩包" prop="file">

            <el-upload
              ref="uploadRef"
              class="upload-dragger-wrapper"
              drag
              :action="uploadUrl"
              :headers="uploadHeaders"
              :data="form"
              :limit="1"
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :on-success="handleSuccess"
              :on-error="handleError"
              :on-exceed="handleExceed"
              :on-progress="handleProgress"
              accept=".zip"
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  仅支持 .zip 格式，文件大小不超过 500MB。
                </div>
              </template>
            </el-upload>
          </el-form-item>
          

          <el-progress 
              v-if="uploadPercentage > 0"
              :percentage="uploadPercentage" 
              :stroke-width="10"
              :text-inside="true"
              status="success"
              class="upload-progress"
            />
  

          <el-form-item class="form-actions">
            <el-button 
              type="primary" 
              size="large"
              :icon="Upload" 
              @click="submitUpload" 
              :loading="isUploading"
              :disabled="!form.file"
            >
              {{ isUploading ? '正在上传...' : '立即上传至服务器' }}
            </el-button>
            <el-button size="large" @click="resetForm">重置所有内容</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </template>
  
  <script setup>
  import { ref, reactive, computed } from 'vue';
  import { Upload, UploadFilled } from '@element-plus/icons-vue';
  import { ElMessage } from 'element-plus';
  import { useUserStore } from '@/stores/userStore';
  
  const uploadFormRef = ref(null);
  const uploadRef = ref(null);
  const userStore = useUserStore();
  
  // --- 状态管理 ---
  const isUploading = ref(false);
  const uploadPercentage = ref(0);
  
  // --- API 配置 ---
  const uploadUrl = `${import.meta.env.VITE_API_URL}/api/shp/upload`;
  const uploadHeaders = computed(() => ({
    Authorization: `Bearer ${userStore.token}`,
  }));
  
  // --- 表单数据与规则 ---
  const initialForm = {
    data_alias: '',
    category: '',
    data_introduction: '',
    file: null,
  };
  const form = reactive({ ...initialForm });
  
  const rules = reactive({
    data_alias: [ { required: true, message: '请输入一个明确的数据名称', trigger: 'blur' } ],
    data_introduction: [ { required: true, message: '数据简介有助于他人理解，不能为空', trigger: 'blur' } ],
    file: [ { required: true, message: '请选择一个 .zip 压缩文件进行上传', trigger: 'change' } ],
  });
  
  // --- 事件处理函数 ---
  const handleFileChange = (uploadFile) => {
    uploadPercentage.value = 0;
    form.file = uploadFile.raw;
    uploadFormRef.value?.validateField('file');
  };
  
  const handleFileRemove = () => {
    form.file = null;
    uploadPercentage.value = 0;
    uploadFormRef.value?.validateField('file');
  };
  
  const handleExceed = () => {
    ElMessage.warning('一次只能上传一个文件，如需更换，请先移除已选文件。');
  };
  
  const handleProgress = (event) => {
    uploadPercentage.value = Math.floor(event.percent);
  };
  
  const submitUpload = async () => {
    if (!uploadFormRef.value) return;
  
    await uploadFormRef.value.validate((valid) => {
      if (valid) {
        isUploading.value = true;
        uploadRef.value?.submit();
      } else {
        ElMessage.error('表单信息不完整，请检查红色标记的必填项。');
      }
    });
  };
  
  const handleSuccess = (response) => {
    isUploading.value = false;
    uploadPercentage.value = 100;
    if (response.code === 200) {
      ElMessage.success('数据上传成功，已入库！');
      setTimeout(resetForm, 1000);
    } else {
      ElMessage.error(response.msg || '上传失败，服务器返回未知错误。');
      uploadPercentage.value = 0;
    }
  };
  
  const handleError = (error) => {
    isUploading.value = false;
    uploadPercentage.value = 0;
    try {
      const errorData = JSON.parse(error.message);
      ElMessage.error(`上传失败: ${errorData.msg || '网络或服务器错误'}`);
    } catch {
      ElMessage.error(`上传失败: ${error.message || '网络或服务器错误'}`);
    }
  };
  
  const resetForm = () => {
    isUploading.value = false;
    uploadPercentage.value = 0;
    Object.assign(form, initialForm);
    uploadRef.value?.clearFiles();
    uploadFormRef.value?.resetFields();
  };
  </script>
  
  <style scoped>
  .data-upload-container {
    padding: 24px 40px;
    background-color: #f7f8fa;
    min-height: calc(100vh - 50px); /* 50px 是顶部 header 的高度 */
  }
  
  .page-header {
    margin-bottom: 24px;
  }
  
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #1d2129;
    margin: 0 0 8px 0;
  }
  
  .page-description {
    font-size: 14px;
    color: #86909c;
    margin: 0;
  }
  
  .upload-main-card {
    border-radius: 8px;
    border: none;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  }
  
  .upload-form {
    padding: 20px;
  }
  
  .upload-form .el-form-item {
    margin-bottom: 24px;
  }
  
  .upload-form .el-form-item__label {
    font-size: 14px;
    font-weight: 500;
    color: #4e5969;
  }
  
  /* 使用 :deep 选择器来修改 el-upload 内部样式 */
  .upload-dragger-wrapper :deep(.el-upload-dragger) {
    padding: 40px;
    border-radius: 8px;
    border: 2px dashed #dcdfe6;
    transition: border-color 0.3s;
  }
  
  .upload-dragger-wrapper :deep(.el-upload-dragger:hover) {
    border-color: var(--el-color-primary);
  }
  
  .el-icon--upload {
    font-size: 50px;
    color: #c0c4cc;
    margin-bottom: 16px;
  }
  
  .el-upload__text {
    color: #606266;
    font-size: 14px;
  }
  
  .el-upload__text em {
    color: var(--el-color-primary);
    font-style: normal;
  }
  
  .el-upload__tip {
    color: #909399;
    font-size: 13px;
    margin-top: 10px;
    text-align: center;
  }
  
  .upload-progress {
    margin-top: -10px;
    margin-bottom: 20px;
  }
  
  .form-actions {
    margin-top: 32px;
    margin-bottom: 0 !important; /* 覆盖默认边距 */
    display: flex;
    justify-content: flex-start;
  }
  .el-select{
      width: 100%;
  }
  </style> -->




  <template>
    <div class="data-upload-container">
      <!-- 1. 页面标题和引导区 -->
      <div class="page-header">
        <h1 class="page-title">数据资源上传</h1>
        <p class="page-description">
          请在此处上传 SHP 格式的地理数据资源。为确保数据一致性，所有文件需打包为 ZIP 压缩文件。
        </p>
      </div>
  
      <!-- 2. 主操作区：表单和上传控件 -->
      <el-card class="upload-main-card">
        <el-form
          ref="uploadFormRef"
          :model="form"
          :rules="rules"
          label-width="120px"
          label-position="top"
          class="upload-form"
          size="large"
        >
          <el-row :gutter="40">
            <el-col :span="12">
              <el-form-item label="数据名称" prop="data_alias">
                <el-input
                  v-model="form.data_alias"
                  placeholder="例如：2023年全国省级行政区划"
                  clearable
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
               <el-form-item label="数据分类 (可选)" prop="category">
                  <el-select v-model="form.category" placeholder="请选择或输入数据分类" filterable allow-create>
                    <el-option label="行政区划" value="行政区划"></el-option>
                    <el-option label="水系" value="水系"></el-option>
                    <el-option label="交通网络" value="交通网络"></el-option>
                    <el-option label="兴趣点 (POI)" value="兴趣点 (POI)"></el-option>
                  </el-select>
                </el-form-item>
            </el-col>
          </el-row>
  
          <el-form-item label="数据简介" prop="data_introduction">
            <el-input
              v-model="form.data_introduction"
              type="textarea"
              :rows="4"
              placeholder="请详细描述数据的来源、坐标系、年份、内容摘要等关键信息，便于其他用户理解和使用。"
              show-word-limit
              maxlength="500"
            />
          </el-form-item>
  
          <el-form-item label="上传 SHP 压缩包" prop="file">
            <!-- el-upload 组件现在只用于选择文件，不进行实际上传 -->
            <el-upload
              ref="uploadRef"
              class="upload-dragger-wrapper"
              drag
              action="#" 
              :limit="1"
              :auto-upload="false"
              :http-request="() => {}"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :on-exceed="handleExceed"
              accept=".zip"
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  仅支持 .zip 格式，文件大小不超过 500MB。
                </div>
              </template>
            </el-upload>
          </el-form-item>
          
          <!-- 上传进度条 -->
          <el-progress 
              v-if="uploadPercentage > 0"
              :percentage="uploadPercentage" 
              :stroke-width="10"
              :text-inside="true"
              status="success"
              class="upload-progress"
            />
  
          <!-- 3. 操作按钮区 -->
          <el-form-item class="form-actions">
            <el-button 
              type="primary" 
              size="large"
              :icon="Upload" 
              @click="submitUpload" 
              :loading="isUploading"
              :disabled="!form.file"
            >
              {{ isUploading ? '正在上传...' : '立即上传至服务器' }}
            </el-button>
            <el-button size="large" @click="resetForm">重置所有内容</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </template>
  
<script setup>
import { ref, reactive } from 'vue';
import { Upload, UploadFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const uploadFormRef = ref(null);
const uploadRef = ref(null);

// --- 状态管理 ---
const isUploading = ref(false);
const uploadPercentage = ref(0);

// --- 表单数据与规则 ---
const initialForm = {
  data_alias: '',
  category: '',
  data_introduction: '',
  file: null, // 用于验证是否有文件
};
const form = reactive({ ...initialForm });

const rules = reactive({
  data_alias: [{ required: true, message: '请输入一个明确的数据名称', trigger: 'blur' }],
  data_introduction: [{ required: true, message: '数据简介有助于他人理解，不能为空', trigger: 'blur' }],
  file: [{ required: true, message: '请选择一个 .zip 压缩文件进行上传', trigger: 'change' }],
});

// --- 事件处理函数 ---
const handleFileChange = (uploadFile) => {
  // 检查文件类型和大小
  const isZip = uploadFile.name.endsWith('.zip');
  const isLt500M = uploadFile.size / 1024 / 1024 < 500;

  if (!isZip) {
    ElMessage.error('只能上传 .zip 格式的文件!');
    uploadRef.value?.clearFiles(); // 清除错误的文件
    form.file = null;
    return;
  }
  if (!isLt500M) {
    ElMessage.error('文件大小不能超过 500MB!');
    uploadRef.value?.clearFiles();
    form.file = null;
    return;
  }
  
  // 文件合法，更新表单状态用于验证
  uploadPercentage.value = 0;
  form.file = uploadFile; // 将文件对象存入 form 中
  uploadFormRef.value?.validateField('file');
};

const handleFileRemove = () => {
  form.file = null;
  uploadPercentage.value = 0;
  // 手动再次验证以清除可能的错误提示
  uploadFormRef.value?.validateField('file');
};

const handleExceed = () => {
  ElMessage.warning('一次只能上传一个文件，如需更换，请先移除已选文件。');
};

// [核心修改] submitUpload 函数，纯前端模拟
const submitUpload = async () => {
  if (!uploadFormRef.value) return;

  // 首先验证表单是否填写完整
  await uploadFormRef.value.validate((valid) => {
    if (valid) {
      // 表单验证通过，开始模拟上传
      isUploading.value = true;
      
      // 1. 模拟一个假的上传进度条
      const interval = setInterval(() => {
        if (uploadPercentage.value < 99) {
          uploadPercentage.value += Math.floor(Math.random() * 15) + 5;
          if (uploadPercentage.value > 99) {
            uploadPercentage.value = 99;
          }
        }
      }, 150); // 每 150ms 更新一次进度

      // 2. 模拟 1.5 秒后上传成功
      setTimeout(() => {
        clearInterval(interval); // 停止进度条
        uploadPercentage.value = 100; // 直接设置为100%
        isUploading.value = false; // 结束 loading 状态
        
        // 3. 显示成功消息
        ElMessage.success('数据上传成功！');
        
        // 4. 稍后重置表单
        setTimeout(resetForm, 1000);
      }, 1500); // 1.5秒后完成
    } else {
      ElMessage.error('表单信息不完整，请检查红色标记的必填项。');
    }
  });
};

const resetForm = () => {
  isUploading.value = false;
  uploadPercentage.value = 0;
  Object.assign(form, initialForm);
  uploadRef.value?.clearFiles();
  // 使用 nextTick 确保DOM更新后再重置表单，避免可能的验证状态残留
  nextTick(() => {
    uploadFormRef.value?.resetFields();
  });
};
</script>
  
<style scoped>
.data-upload-container {
  padding: 24px 40px;
  background-color: #f7f8fa;
  min-height: calc(100vh - 50px);
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1d2129;
  margin: 0 0 8px 0;
}
.page-description {
  font-size: 14px;
  color: #86909c;
  margin: 0;
}
.upload-main-card {
  border-radius: 8px;
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
.upload-form {
  padding: 20px;
}
.upload-form .el-form-item {
  margin-bottom: 24px;
}
.upload-form .el-form-item__label {
  font-size: 14px;
  font-weight: 500;
  color: #4e5969;
}
.upload-dragger-wrapper :deep(.el-upload-dragger) {
  padding: 40px;
  border-radius: 8px;
  border: 2px dashed #dcdfe6;
  transition: border-color 0.3s;
}
.upload-dragger-wrapper :deep(.el-upload-dragger:hover) {
  border-color: var(--el-color-primary);
}
.el-icon--upload {
  font-size: 50px;
  color: #c0c4cc;
  margin-bottom: 16px;
}
.el-upload__text {
  color: #606266;
  font-size: 14px;
}
.el-upload__text em {
  color: var(--el-color-primary);
  font-style: normal;
}
.el-upload__tip {
  color: #909399;
  font-size: 13px;
  margin-top: 10px;
  text-align: center;
}
.upload-progress {
  margin-top: -10px;
  margin-bottom: 20px;
}
.form-actions {
  margin-top: 32px;
  margin-bottom: 0 !important;
  display: flex;
  justify-content: flex-start;
}
.el-select{
    width: 100%;
}
</style>