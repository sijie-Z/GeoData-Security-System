<!-- <template>
  <div>
    <el-table :data="data.list" border>
      <el-table-column prop="id" label="申请编号" width="85" />
      <el-table-column prop="data_alias" label="数据名称" width="85"/>
      <el-table-column prop="data_id" label="矢量数据编号" width="110"/>
      <el-table-column prop="applicant_user_number" label="申请人编号" width="100"/>
      <el-table-column prop="applicant_name" label="申请人姓名" width="100"/>
      <el-table-column prop="adm1_name" label="一审人员姓名" width="120"/>
      <el-table-column prop="adm2_name" label="二审人员姓名" width="120"/>

      <el-table-column label="一审状态" width="100">
        <template v-slot="scope">
          {{ getStatusText(scope.row.first_statu) }}
        </template>
      </el-table-column>

      <el-table-column label="二审状态" width="100">
        <template v-slot="scope">
          <div v-if="!scope.row.first_statu">
            {{ getStatusText('空') }}
          </div>
          <div v-else>
            {{ getStatusText(scope.row.second_statu) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="水印">
        <template #default="scope">
          <el-image class="qr-code-image"
            :src="scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : ''"
            :preview-src-list="[scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : '']"
            fit="cover"
            style="width: 50px; height: 50px;"
          />
        </template>
      </el-table-column>

      <el-table-column label="操作" width="122.5">
        <template v-slot="scope">
          <el-button size="small" type="primary" @click="openRequestDialog(scope.row)">生成水印</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>

  <div>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="prev, pager, next, jumper, total"
      @current-change="pageChanged"
      class="view-pagination"
    />
  </div>

  <el-dialog
    v-model="requestDataVisible"
    width="550px"
    :before-close="(done)=>handleClose('request',done)"
    :show-close="true"
    :close-on-click-modal="false"
    class="custom-watermark-dialog"
    title=""
  >

    <el-form ref="requestFormRef" :model="requestInformation" status-icon :rules="rules" label-position="left" label-width="90px">

      <el-divider content-position="left" class="section-divider">水印信息</el-divider>
      <el-form-item label="申请编号" prop="application_id" required>
        <el-input v-model="requestInformation.application_id" placeholder="请填写申请编号" />
      </el-form-item>
      <el-form-item label="数据编号" prop="data_id">
        <el-input v-model="requestInformation.data_id" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="数据名称" prop="data_alias">
        <el-input v-model="requestInformation.data_alias" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="申请人姓名" prop="applicant_name">
        <el-input v-model="requestInformation.applicant_name" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="员工编号" prop="applicant_user_number">
        <el-input v-model="requestInformation.applicant_user_number" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="一审人员" prop="adm1_name">
        <el-input v-model="requestInformation.adm1_name" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="二审人员" prop="adm2_name">
        <el-input v-model="requestInformation.adm2_name" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="生成时间" prop="now">
        <el-input v-model="requestInformation.now" placeholder="自动填充" />
      </el-form-item>

      <el-divider content-position="left" class="section-divider">数据选项</el-divider>
      <el-form-item label="数据格式" prop="data_format">
        <el-select v-model="requestInformation.data_format" placeholder="请选择" style="width: 100%;">
          <el-option label="Shapefile" value="shapefile"></el-option>
          <el-option label="GeoJSON" value="geojson"></el-option>
          <el-option label="KML" value="kml"></el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="比例尺" prop="scale">
        <el-select v-model="requestInformation.scale" placeholder="请选择" style="width: 100%;">
          <el-option label="自动" value="auto"></el-option>
          <el-option label="1:10,000" value="1:10000"></el-option>
          <el-option label="1:50,000" value="1:50000"></el-option>
          <el-option label="1:250,000" value="1:250000"></el-option>
        </el-select>
      </el-form-item>

      <el-divider content-position="left" class="section-divider">输入输出路径</el-divider>
      <el-form-item label="输入路径" prop="input_path">
        <div style="display: flex; align-items: center; width: 100%;">
          <el-input v-model="requestInformation.input_path" placeholder="请填写" style="flex-grow: 1; margin-right: 10px;"/>
          <el-button type="primary" size="small">浏览...</el-button>
        </div>
      </el-form-item>

      <el-form-item label="输出路径" prop="output_path">
        <div style="display: flex; align-items: center; width: 100%;">
          <el-input v-model="requestInformation.output_path" placeholder="请填写" style="flex-grow: 1; margin-right: 10px;"/>
          
          <el-button type="primary" size="small">浏览...</el-button>
        </div>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="generate">确认生成</el-button>
        <el-button @click="resetForm">重置</el-button>
      </el-form-item>
    </el-form>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, onMounted, watch, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from 'axios';

const data = reactive({ list: [] });
const page = ref(1);
const pageSize = ref(2);
const total = ref(0);
const requestDataVisible = ref(false);
const requestFormRef = ref(null);


watch(page, (newValue, oldValue) => {
  if (oldValue !== newValue) {
    get_applications();
  }
});

const pageChanged = (newPage) => {
  page.value = newPage;
};

const getStatusText = (status) => {
  if (status === true) return '通过';
  if (status === false) return '不通过';
  if (status === null) return '待审核';
  return ''; // 默认返回空字符串
};

const rules = {
  application_id: [{ required: true, message: '请填写申请编号', trigger: 'blur' }], // 新增或修改此行
  data_id: [{ required: true, message: '请填写数据编号', trigger: 'blur' }],
  data_alias: [{ required: true, message: '请填写数据名称', trigger: 'blur' }],
  applicant_name: [{ required: true, message: '请填写申请人姓名', trigger: 'blur' }],
  applicant_user_number: [{ required: true, message: '请填写员工编号', trigger: 'blur' }],
  adm1_name: [{ required: true, message: '请填写一审人员姓名', trigger: 'blur' }],
  adm2_name: [{ required: true, message: '请填写二审人员姓名', trigger: 'blur' }],
  now: [{ required: true, message: '请填写生成水印的时间', trigger: 'blur' }],
  // [新增开始] 新增字段的验证规则 (您可以根据需要设为必填或添加其他规则)
  data_format: [{ message: '请选择数据格式', trigger: 'change' }], // 示例：非必填
  scale: [{ message: '请选择或输入比例尺', trigger: 'change' }], // 示例：非必填
  input_path: [{ message: '请填写输入路径', trigger: 'blur' }], // 示例：非必填
  output_path: [{ message: '请填写输出路径', trigger: 'blur' }], // 示例：非必填
  // [新增结束]
  // copy_data 通常不需要验证规则
};

const initialRequestInformation = {
  application_id: '',
  data_id: '',
  data_alias: '',
  applicant_name: '',
  applicant_user_number: '',
  adm1_name: '',
  adm2_name: '',
  now: '',
  // [新增开始] 为“水印嵌入”功能预留的字段
  data_format: '', // 数据格式
  scale: 'auto',       // 比例尺，默认为“自动”
  input_path: '',  // 输入路径
  output_path: '',  // 输出路径
  copy_data: false // [新增] 复制数据选项，默认为false
  // [新增结束]
};

const requestInformation = reactive({ ...initialRequestInformation });

const get_applications = async () => {
  try {
    const response = await axios.get('http://localhost:5001/api/adm1_get_applications_generate_watermark', {
      params: { page: page.value, pageSize: pageSize.value },
      responseType: 'json'
    });

    if (!response.data || !response.data.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data.msg || '获取记录失败');
      return;
    }

    data.list = response.data.application_data;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error('Error fetching records:', err);
    ElMessage.error('获取记录失败');
  }
};

onMounted(() => {
  get_applications();
});


const openRequestDialog = (row) => {
  Object.assign(requestInformation, {
    application_id: row.id,
    data_id: row.data_id,
    data_alias: row.data_alias,
    applicant_name: row.applicant_name,
    applicant_user_number: row.applicant_user_number,
    adm1_name: row.adm1_name,
    adm2_name: row.adm2_name,
    now: new Date().toLocaleString(),
    // [新增开始] 打开弹窗时，如果需要从row中获取这些新字段的默认值，可以在这里设置
    // 例如: data_format: row.default_data_format || '',
    // 如果没有默认值，则会使用 initialRequestInformation 中的空字符串
    data_format: initialRequestInformation.data_format, // 使用初始默认值
    scale: initialRequestInformation.scale,             // 使用初始默认值
    input_path: initialRequestInformation.input_path,   // 使用初始默认值
    output_path: initialRequestInformation.output_path, // 使用初始默认值
    copy_data: initialRequestInformation.copy_data      // 使用初始默认值
    // [新增结束]
  });
  requestDataVisible.value = true;
};

const resetForm = async () => {
  Object.assign(requestInformation, { ...initialRequestInformation });
  await nextTick();
  requestFormRef.value?.clearValidate();
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('确认关闭？').then(() => {
    done();
    if (dialogType === 'request') {
      resetForm();
    }
  }).catch(() => {});
};

const generate = () => {
  requestFormRef.value.validate((valid) => {
    if (valid) {
      axios.post('http://localhost:5001/api/generate_watermark', requestInformation)
        .then((response) => {
          if (response.data.status) {
            ElMessage.success('生成水印成功');
            get_applications(); // 刷新记录
            requestDataVisible.value = false;
          } else {
            ElMessage.error(response.data.msg || '生成水印失败');
          }
        }).catch((err) => {
          console.error('Error generating watermark:', err);
          ElMessage.error('生成水印失败');
        });
      get_applications()

    } else {
      console.log('表单验证失败');
    }
  });
};

const handleImageError = (scope) => {
  scope.row.qrcode = ''; // 设置默认图片路径
};

</script>

<style>
.qr-code-image {
  width: 50px;
  height: 50px;
}

.view-pagination{
  margin-top: 20px;
}


.custom-watermark-dialog .el-dialog__header {
  /* [修改] 将背景色改为渐变 */
  background-image: linear-gradient(to bottom, #2A6EB3, #58A9FF); /* 深蓝到浅蓝的渐变 */
  padding: 8px 15px;      /* [修改] 进一步减小内边距，使其更紧凑 */
  border-top-left-radius: 4px; 
  border-top-right-radius: 4px;
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: 15px; /* [修改] 进一步减小标题栏和下方内容的间距 */
}

/* 在header中添加“申请使用数据”文字 */
.custom-watermark-dialog .el-dialog__header::before {
  content: "申请使用数据";
  color: white;
  font-size: 16px; /* [修改] 标题字体大小略微调小以适应更紧凑的头部 */
  font-weight: bold;
}

/* 隐藏 Element Plus 默认的 title span */
.custom-watermark-dialog .el-dialog__title {
  display: none; 
}

/* 修改关闭按钮 (×) 的样式 */
.custom-watermark-dialog .el-dialog__headerbtn {
  position: static; 
  height: auto;
  width: auto;
}
.custom-watermark-dialog .el-dialog__headerbtn .el-dialog__close {
  color: red !important; 
  font-size: 16px; /* [修改] 关闭按钮大小与标题字体协调 */
}
.custom-watermark-dialog .el-dialog__headerbtn .el-dialog__close:hover {
  color: darkred !important; 
}


/* 调整 Element Plus 分割线内文字的样式 */
.custom-watermark-dialog .section-divider .el-divider__text {
  font-size: 14px; /* [修改] 分区标题字体大小略微调小 */
  font-weight: bold;
  color: #303133; 
  padding: 0 10px; /* [修改] 减小内边距 */
}
.custom-watermark-dialog .el-divider--horizontal{
  margin: 15px 0; /* [修改] 减小分割线上下的间距 */
}

/* 调整表单标签字体大小和对齐 */
.custom-watermark-dialog .el-form-item__label {
  font-size: 13px;
  color: #606266; 
  padding-right: 8px; /* [修改] 减小标签和输入框之间的间距 */
  line-height: 32px; 
  height: 32px; /* [新增] 确保标签高度与输入框一致 */
  display: inline-flex; /* [新增] 使用flex布局进行垂直居中 */
  align-items: center; /* [新增] 垂直居中标签内文字（包括星号）*/
}

/* 表单项的垂直间距 */
.custom-watermark-dialog .el-form-item {
  margin-bottom: 10px; /* [修改] 进一步减小行间距 */
}

.custom-watermark-dialog .el-input__inner,
.custom-watermark-dialog .el-select .el-input__inner,
.custom-watermark-dialog .el-textarea__inner {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-size: 13px;
  height: 32px;
  line-height: 32px;
  padding-right: 140px !important; /* 修改：增加右内边距，为错误提示和图标预留空间 */
}

/* 针对选择框的下拉箭头等也需要调整一下大小和对齐 */
.custom-watermark-dialog .el-select .el-input .el-select__caret {
  font-size: 13px; /* [修改] 调整下拉箭头大小 */
}


.custom-watermark-dialog .el-dialog {
  border: 2px solid #2A6EB3; /* 暗蓝色边框 */
  border-radius: 6px;
  overflow: hidden; /* 确保边框圆角正常显示 */
}

/* 调整按钮之间的间距 */
.custom-watermark-dialog .el-form-item:last-child .el-button + .el-button {
  margin-left: 80px; /* 增加按钮之间的间距 */
}

/* 调整按钮组的样式 (通常是最后一个表单项) */
.custom-watermark-dialog .el-form-item:last-child {
  margin-bottom: 0; /* 最后一个表单项通常不需要底部外边距 */
  margin-top: 20px; /* 修改：减小与上方表单的距离，比如从 40px 改为 20px */
  text-align: center; /* 按钮居中显示 */
}

/* 调整按钮之间的间距 */
.custom-watermark-dialog .el-form-item:last-child .el-button + .el-button {
  margin-left: 120px; /* 修改：增加按钮之间的间距，比如从 80px 改为 120px，让重置按钮更靠右 */
}

/* 调整浏览按钮的样式，使其更紧凑 */
.custom-watermark-dialog .el-form-item .el-button--small {
    padding: 5px 10px; /* [修改] 针对浏览按钮这种small类型的按钮进一步减小padding */
    font-size: 13px; 
}

/* [新增] 调整复选框的样式 */
.custom-watermark-dialog .el-checkbox__label {
  font-size: 13px; /* [修改] 复选框标签文字大小从 12px 增加到 13px */
  padding-left: 8px; /* [修改] 调整复选框与文字间距 */
}
.custom-watermark-dialog .el-checkbox__inner {
  width: 15px; /* [修改] 适当调整复选框大小 */
  height: 15px;
}
.custom-watermark-dialog .el-checkbox__inner::after { /* 调整勾号大小和位置 */
    height: 8px;
    left: 4px; /* 可能需要微调 */
    top: 1px;  /* 可能需要微调 */
    width: 4px;/* 可能需要微调 */
}

/* [新增结束] */

/* 调整表单验证提示的位置和样式 */
.custom-watermark-dialog .el-form-item__error {
  position: absolute;
  top: 50%; /* 垂直居中 */
  transform: translateY(-50%); /* 精确垂直居中 */
  right: 40px; /* 修改：定位到输入框内部右侧，验证图标的左边 */
  font-size: 12px;
  line-height: 1; /* 确保单行文字的行高 */
  color: #F56C6C;
  z-index: 1; /* 确保在输入内容之上 */
  background-color: transparent;
  padding: 0 2px;
  pointer-events: none; /* 错误信息不捕获鼠标事件，以免干扰输入 */

  /* 处理可能过长的错误信息 */
  max-width: 95px; /* 修改：最大宽度，避免遮挡验证图标或溢出过多 */
  white-space: nowrap; /* 不换行 */
  overflow: hidden; /* 超出部分隐藏 */
  text-overflow: ellipsis; /* 超出部分显示省略号 */
}

/* 调整输入框和选择框的样式，为右侧的错误提示和状态图标留出空间 */
.custom-watermark-dialog .el-input__inner,
.custom-watermark-dialog .el-select .el-input__inner {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-size: 13px;
  height: 32px;
  line-height: 32px;
  /* 修改：显著增加右内边距，以容纳错误提示文字和状态图标 */
  /* 这个值需要根据您最长的错误提示和图标宽度来调整 */
  /* 假设状态图标约20-25px宽，错误提示最长如“请填写一审人员姓名”约100-120px */
  padding-right: 160px; /* 示例值，请根据实际情况调整 */
}


/* 调整按钮组的样式 (通常是最后一个表单项) */
.custom-watermark-dialog .el-form-item:last-child {
  margin-bottom: 0;
  margin-top: 10px; /* 修改：减小与上方表单的距离，例如从 20px 改为 10px */
  text-align: center;
}

/* 调整按钮之间的间距 */
.custom-watermark-dialog .el-form-item:last-child .el-button + .el-button {
  margin-left: 150px; /* 修改：进一步增加按钮之间的间距，例如从 120px 改为 150px */
}

/* 确保输入框内部有足够空间显示错误信息 */
.custom-watermark-dialog .el-input__inner {
  padding-right: 30px; /* 为错误信息预留空间 */
}
</style> -->


<!-- <template>
  <div class="watermark-generation-container">
    <el-table :data="data.list" border>
      <el-table-column prop="id" label="申请编号" width="85" />
      <el-table-column prop="data_alias" label="数据名称" width="85" />
      <el-table-column prop="data_id" label="矢量数据编号" width="110" />
      <el-table-column prop="applicant_user_number" label="申请人编号" width="100" />
      <el-table-column prop="applicant_name" label="申请人姓名" width="100" />
      <el-table-column prop="adm1_name" label="一审人员姓名" width="120" />
      <el-table-column prop="adm2_name" label="二审人员姓名" width="120" />

      <el-table-column label="一审状态" width="100">
        <template v-slot="scope">
          {{ getStatusText(scope.row.first_statu) }}
        </template>
      </el-table-column>

      <el-table-column label="二审状态" width="100">
        <template v-slot="scope">
          <div v-if="!scope.row.first_statu">
            {{ getStatusText('空') }}
          </div>
          <div v-else>
            {{ getStatusText(scope.row.second_statu) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="水印">
        <template #default="scope">
          <el-image
            class="qr-code-image"
            :src="scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : ''"
            :preview-src-list="[scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : '']"
            fit="cover"
            style="width: 50px; height: 50px;"
          />
        </template>
      </el-table-column>

      <el-table-column label="操作" width="122.5">
        <template v-slot="scope">
          <el-button size="small" type="primary" @click="openRequestDialog(scope.row)">生成水印</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="prev, pager, next, jumper, total"
        class="view-pagination"
      />
    </div>

    <el-dialog
      v-model="requestDataVisible"
      width="550px"
      :before-close="done => handleClose('request', done)"
      :show-close="true"
      :close-on-click-modal="false"
      class="custom-watermark-dialog"
      title=""
    >
      <el-form
        ref="requestFormRef"
        :model="requestInformation"
        status-icon
        :rules="rules"
        label-position="left"
        label-width="90px"
      >
        <el-divider content-position="left" class="section-divider">水印信息</el-divider>
        <el-form-item label="申请编号" prop="application_id" required>
          <el-input v-model="requestInformation.application_id" placeholder="请填写申请编号" />
        </el-form-item>
        <el-form-item label="数据编号" prop="data_id">
          <el-input v-model="requestInformation.data_id" placeholder="请填写" />
        </el-form-item>
        <el-form-item label="数据名称" prop="data_alias">
          <el-input v-model="requestInformation.data_alias" placeholder="请填写" />
        </el-form-item>
        <el-form-item label="申请人姓名" prop="applicant_name">
          <el-input v-model="requestInformation.applicant_name" placeholder="请填写" />
        </el-form-item>
        <el-form-item label="员工编号" prop="applicant_user_number">
          <el-input v-model="requestInformation.applicant_user_number" placeholder="请填写" />
        </el-form-item>
        <el-form-item label="一审人员" prop="adm1_name">
          <el-input v-model="requestInformation.adm1_name" placeholder="请填写" />
        </el-form-item>
        <el-form-item label="二审人员" prop="adm2_name">
          <el-input v-model="requestInformation.adm2_name" placeholder="请填写" />
        </el-form-item>
        <el-form-item label="生成时间" prop="now">
          <el-input v-model="requestInformation.now" placeholder="自动填充" />
        </el-form-item>

        <el-divider content-position="left" class="section-divider">数据选项</el-divider>
        <el-form-item label="数据格式" prop="data_format">
          <el-select v-model="requestInformation.data_format" placeholder="请选择" style="width: 100%;">
            <el-option label="Shapefile" value="shapefile"></el-option>
            <el-option label="GeoJSON" value="geojson"></el-option>
            <el-option label="KML" value="kml"></el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="比例尺" prop="scale">
          <el-select v-model="requestInformation.scale" placeholder="请选择" style="width: 100%;">
            <el-option label="自动" value="auto"></el-option>
            <el-option label="1:10,000" value="1:10000"></el-option>
            <el-option label="1:50,000" value="1:50000"></el-option>
            <el-option label="1:250,000" value="1:250000"></el-option>
          </el-select>
        </el-form-item>

        <el-divider content-position="left" class="section-divider">输入输出路径</el-divider>
        <el-form-item label="输入路径" prop="input_path">
          <div style="display: flex; align-items: center; width: 100%;">
            <el-input v-model="requestInformation.input_path" placeholder="请填写" style="flex-grow: 1; margin-right: 10px;" />
            <el-button type="primary" size="small">浏览...</el-button>
          </div>
        </el-form-item>

        <el-form-item label="输出路径" prop="output_path">
          <div style="display: flex; align-items: center; width: 100%;">
            <el-input v-model="requestInformation.output_path" placeholder="请填写" style="flex-grow: 1; margin-right: 10px;" />
            <el-button type="primary" size="small">浏览...</el-button>
          </div>
        </el-form-item>

        <el-form-item class="dialog-buttons">
          <el-button type="primary" @click="generate">确认生成</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, watch, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from 'axios';

// 数据状态
const data = reactive({ list: [] });
const page = ref(1);
const pageSize = ref(10); // 调整每页显示数量
const total = ref(0);
const requestDataVisible = ref(false);
const requestFormRef = ref(null);

// 监听页码变化，自动重新获取数据
watch(page, (newPage) => {
  get_applications();
});

// 获取申请记录列表
const get_applications = async () => {
  try {
    // ⚠ 重要：这里的 API URL 必须与您的后端路由完全匹配，否则会报 404
    // 您的代码中是 adm1，但您给的错误信息是 adm2，请确保这里和后端保持一致
    const response = await axios.get('http://localhost:5001/api/adm1_get_applications_generate_watermark', {
      params: { page: page.value, pageSize: pageSize.value.value },
      responseType: 'json'
    });

    if (!response.data || !response.data.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data.msg || '获取记录失败');
      return;
    }

    data.list = response.data.application_data;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error('Error fetching records:', err);
    ElMessage.error('获取记录失败，请检查网络或后端接口地址');
  }
};

// 表格状态文本格式化
const getStatusText = (status) => {
  if (status === true) return '通过';
  if (status === false) return '不通过';
  if (status === null) return '待审核';
  return '';
};

// 表单验证规则
const rules = {
  application_id: [{ required: true, message: '请填写申请编号', trigger: 'blur' }],
  data_id: [{ required: true, message: '请填写数据编号', trigger: 'blur' }],
  data_alias: [{ required: true, message: '请填写数据名称', trigger: 'blur' }],
  applicant_name: [{ required: true, message: '请填写申请人姓名', trigger: 'blur' }],
  applicant_user_number: [{ required: true, message: '请填写员工编号', trigger: 'blur' }],
  adm1_name: [{ required: true, message: '请填写一审人员姓名', trigger: 'blur' }],
  adm2_name: [{ required: true, message: '请填写二审人员姓名', trigger: 'blur' }],
  now: [{ required: true, message: '请填写生成水印的时间', trigger: 'blur' }],
};

const initialRequestInformation = {
  application_id: '',
  data_id: '',
  data_alias: '',
  applicant_name: '',
  applicant_user_number: '',
  adm1_name: '',
  adm2_name: '',
  now: '',
  data_format: '',
  scale: 'auto',
  input_path: '',
  output_path: '',
};

const requestInformation = reactive({ ...initialRequestInformation });

// 打开对话框并填充数据
const openRequestDialog = (row) => {
  Object.assign(requestInformation, {
    application_id: row.id,
    data_id: row.data_id,
    data_alias: row.data_alias,
    applicant_name: row.applicant_name,
    applicant_user_number: row.applicant_user_number,
    adm1_name: row.adm1_name,
    adm2_name: row.adm2_name,
    now: new Date().toLocaleString(),
    data_format: initialRequestInformation.data_format,
    scale: initialRequestInformation.scale,
    input_path: initialRequestInformation.input_path,
    output_path: initialRequestInformation.output_path,
  });
  requestDataVisible.value = true;
};

// 重置表单
const resetForm = async () => {
  Object.assign(requestInformation, { ...initialRequestInformation });
  await nextTick();
  requestFormRef.value?.clearValidate();
};

// 关闭对话框
const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('确认关闭？').then(() => {
    done();
    if (dialogType === 'request') {
      resetForm();
    }
  }).catch(() => {});
};

// 生成水印
const generate = () => {
  requestFormRef.value.validate((valid) => {
    if (valid) {
      // ⚠ 重要：这里的 API URL 必须与您的后端路由完全匹配
      axios.post('http://localhost:5001/api/generate_watermark', requestInformation)
        .then((response) => {
          if (response.data.status) {
            ElMessage.success('生成水印成功');
            get_applications(); // 刷新记录
            requestDataVisible.value = false;
          } else {
            ElMessage.error(response.data.msg || '生成水印失败');
          }
        }).catch((err) => {
          console.error('Error generating watermark:', err);
          ElMessage.error('生成水印失败');
        });
    } else {
      console.log('表单验证失败');
    }
  });
};

onMounted(() => {
  get_applications();
});
</script>

<style scoped>
.watermark-generation-container {
  padding: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.qr-code-image {
  width: 50px;
  height: 50px;
}

.custom-watermark-dialog .el-dialog__header {
  background-image: linear-gradient(to bottom, #2a6eb3, #58a9ff);
  padding: 8px 15px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.custom-watermark-dialog .el-dialog__header::before {
  content: "申请使用数据";
  color: white;
  font-size: 16px;
  font-weight: bold;
}

.custom-watermark-dialog .el-dialog__title {
  display: none;
}

.custom-watermark-dialog .el-dialog__headerbtn {
  position: static;
  height: auto;
  width: auto;
}

.custom-watermark-dialog .el-dialog__headerbtn .el-dialog__close {
  color: red !important;
  font-size: 16px;
}

.custom-watermark-dialog .el-dialog__headerbtn .el-dialog__close:hover {
  color: darkred !important;
}

.custom-watermark-dialog .section-divider .el-divider__text {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  padding: 0 10px;
}

.custom-watermark-dialog .el-divider--horizontal {
  margin: 15px 0;
}

.custom-watermark-dialog .el-form-item__label {
  font-size: 13px;
  color: #606266;
  padding-right: 8px;
  line-height: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
}

.custom-watermark-dialog .el-form-item {
  margin-bottom: 10px;
}

.custom-watermark-dialog .el-input__inner,
.custom-watermark-dialog .el-select .el-input__inner,
.custom-watermark-dialog .el-textarea__inner {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-size: 13px;
  height: 32px;
  line-height: 32px;
}

.custom-watermark-dialog .el-select .el-input .el-select__caret {
  font-size: 13px;
}

.custom-watermark-dialog .el-dialog {
  border: 2px solid #2a6eb3;
  border-radius: 6px;
  overflow: hidden;
}

.custom-watermark-dialog .dialog-buttons {
  margin-top: 10px;
  text-align: center;
}

.custom-watermark-dialog .dialog-buttons .el-button + .el-button {
  margin-left: 150px;
}

.custom-watermark-dialog .el-form-item .el-button--small {
  padding: 5px 10px;
  font-size: 13px;
}

.custom-watermark-dialog .el-checkbox__label {
  font-size: 13px;
  padding-left: 8px;
}

.custom-watermark-dialog .el-checkbox__inner {
  width: 15px;
  height: 15px;
}

.custom-watermark-dialog .el-checkbox__inner::after {
  height: 8px;
  left: 4px;
  top: 1px;
  width: 4px;
}

.custom-watermark-dialog .el-form-item__error {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  right: 40px;
  font-size: 12px;
  line-height: 1;
  color: #f56c6c;
  z-index: 1;
  background-color: transparent;
  padding: 0 2px;
  pointer-events: none;
  max-width: 95px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style> -->




<template>
  <div>
    <el-table :data="data.list" border>
      <el-table-column prop="id" label="申请编号" width="85" />
      <el-table-column prop="data_alias" label="数据名称" width="85"/>
      <el-table-column prop="data_id" label="矢量数据编号" width="110"/>
      <el-table-column prop="applicant_user_number" label="申请人编号" width="100"/>
      <el-table-column prop="applicant_name" label="申请人姓名" width="100"/>
      <el-table-column prop="adm1_name" label="一审人员姓名" width="120"/>
      <el-table-column prop="adm2_name" label="二审人员姓名" width="120"/>

      <el-table-column label="一审状态" width="100">
        <template v-slot="scope">
          {{ getStatusText(scope.row.first_statu) }}
        </template>
      </el-table-column>

      <el-table-column label="二审状态" width="100">
        <template v-slot="scope">
          <div v-if="!scope.row.first_statu">
            {{ getStatusText('空') }}
          </div>
          <div v-else>
            {{ getStatusText(scope.row.second_statu) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="水印">
        <template #default="scope">
          <el-image class="qr-code-image"
            :src="scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : ''"
            :preview-src-list="[scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : '']"
            fit="cover"
            style="width: 50px; height: 50px;"
          />
        </template>
      </el-table-column>

      <el-table-column label="操作" width="122.5">
        <template v-slot="scope">
          <el-button size="small" type="primary" @click="openRequestDialog(scope.row)">生成水印</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>

  <div>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="prev, pager, next, jumper, total"
      @current-change="pageChanged"
      class="view-pagination"
    />
  </div>

   <!-- [删除开始] 下面这个 el-dialog 将被删除 -->
  <!-- 
  <el-dialog title="申请使用数据" v-model="requestDataVisible" width="50%" :before-close="(done)=>handleClose('request',done)">
    <el-form ref="requestFormRef" :model="requestInformation" status-icon :rules="rules">
      <el-form-item label="编号" prop="application_id">
        <el-input v-model="requestInformation.application_id" placeholder="请填写申请编号" readonly/>
      </el-form-item>
      <el-form-item label="数据编号" prop="data_id">
        <el-input v-model="requestInformation.data_id" placeholder="请填写数据编号" />
      </el-form-item>
      <el-form-item label="数据名称" prop="data_alias">
        <el-input v-model="requestInformation.data_alias" placeholder="请填写数据名称" />
      </el-form-item>
      <el-form-item label="申请人姓名" prop="applicant_name">
        <el-input v-model="requestInformation.applicant_name" placeholder="请填写申请人姓名" />
      </el-form-item>
      <el-form-item label="员工编号" prop="applicant_user_number">
        <el-input v-model="requestInformation.applicant_user_number" placeholder="请填写员工编号" />
      </el-form-item>
      <el-form-item label="一审人员姓名" prop="adm1_name">
        <el-input v-model="requestInformation.adm1_name" placeholder="请填写一审人员姓名" />
      </el-form-item>
      <el-form-item label="二审人员姓名" prop="adm2_name">
        <el-input v-model="requestInformation.adm2_name" placeholder="请填写二审人员姓名" />
      </el-form-item>
      <el-form-item label="水印生成时间" prop="now">
        <el-input v-model="requestInformation.now" placeholder="请填写水印生成时间" />
      </el-form-item>

      <el-form-item label="数据格式" prop="data_format">
        <el-select v-model="requestInformation.data_format" placeholder="请选择数据格式">
          <el-option label="Shapefile" value="shapefile"></el-option>
          <el-option label="GeoJSON" value="geojson"></el-option>
          <el-option label="KML" value="kml"></el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="比例尺" prop="scale">
        <el-input v-model="requestInformation.scale" placeholder="例如: 1:10000 或 自动" />
      </el-form-item>

      <el-form-item label="输入路径" prop="input_path">
        <el-input v-model="requestInformation.input_path" placeholder="请填写数据输入路径" />
      </el-form-item>

      <el-form-item label="输出路径" prop="output_path">
        <el-input v-model="requestInformation.output_path" placeholder="请填写数据输出路径" />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="generate">确认生成</el-button>
        <el-button @click="resetForm">重置</el-button>
      </el-form-item>
    </el-form>
  </el-dialog>
  -->
  <!-- [删除结束] -->


  <el-dialog
    v-model="requestDataVisible"
    width="550px"
    :before-close="(done)=>handleClose('request',done)"
    :show-close="true"
    :close-on-click-modal="false"
    class="custom-watermark-dialog"
    title=""
  >
    <!-- 我们将通过 CSS 直接在 el-dialog__header 中创建标题 -->
    <el-form ref="requestFormRef" :model="requestInformation" status-icon :rules="rules" label-position="left" label-width="90px">
      <!-- 水印信息区域 -->
      <el-divider content-position="left" class="section-divider">水印信息</el-divider>
      <el-form-item label="申请编号" prop="application_id" required>
        <el-input v-model="requestInformation.application_id" placeholder="请填写申请编号" />
      </el-form-item>
      <el-form-item label="数据编号" prop="data_id">
        <el-input v-model="requestInformation.data_id" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="数据名称" prop="data_alias">
        <el-input v-model="requestInformation.data_alias" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="申请人姓名" prop="applicant_name">
        <el-input v-model="requestInformation.applicant_name" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="员工编号" prop="applicant_user_number">
        <el-input v-model="requestInformation.applicant_user_number" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="一审人员" prop="adm1_name">
        <el-input v-model="requestInformation.adm1_name" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="二审人员" prop="adm2_name">
        <el-input v-model="requestInformation.adm2_name" placeholder="请填写" />
      </el-form-item>
      <el-form-item label="生成时间" prop="now">
        <el-input v-model="requestInformation.now" placeholder="自动填充" />
      </el-form-item>

      <!-- 数据选项区域 -->
      <el-divider content-position="left" class="section-divider">数据选项</el-divider>
      <el-form-item label="数据格式" prop="data_format">
        <el-select v-model="requestInformation.data_format" placeholder="请选择" style="width: 100%;">
          <el-option label="Shapefile" value="shapefile"></el-option>
          <el-option label="GeoJSON" value="geojson"></el-option>
          <el-option label="KML" value="kml"></el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="比例尺" prop="scale">
        <el-select v-model="requestInformation.scale" placeholder="请选择" style="width: 100%;">
          <el-option label="自动" value="auto"></el-option>
          <el-option label="1:10,000" value="1:10000"></el-option>
          <el-option label="1:50,000" value="1:50000"></el-option>
          <el-option label="1:250,000" value="1:250000"></el-option>
        </el-select>
      </el-form-item>

      <!-- 输入输出路径区域 -->
      <el-divider content-position="left" class="section-divider">输入输出路径</el-divider>
      <el-form-item label="输入路径" prop="input_path">
        <div style="display: flex; align-items: center; width: 100%;">
          <el-input v-model="requestInformation.input_path" placeholder="请填写" style="flex-grow: 1; margin-right: 10px;"/>
          <el-button type="primary" size="small">浏览...</el-button>
        </div>
      </el-form-item>

      <el-form-item label="输出路径" prop="output_path">
        <div style="display: flex; align-items: center; width: 100%;">
          <el-input v-model="requestInformation.output_path" placeholder="请填写" style="flex-grow: 1; margin-right: 10px;"/>
          
          <el-button type="primary" size="small">浏览...</el-button>
        </div>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="generate">确认生成</el-button>
        <el-button @click="resetForm">重置</el-button>
      </el-form-item>
    </el-form>
  </el-dialog>
</template>

<script setup>
import { reactive, ref, onMounted, watch, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from 'axios';

const data = reactive({ list: [] });
const page = ref(1);
const pageSize = ref(2);
const total = ref(0);
const requestDataVisible = ref(false);
const requestFormRef = ref(null);


watch(page, (newValue, oldValue) => {
  if (oldValue !== newValue) {
    get_applications();
  }
});

const pageChanged = (newPage) => {
  page.value = newPage;
};

const getStatusText = (status) => {
  if (status === true) return '通过';
  if (status === false) return '不通过';
  if (status === null) return '待审核';
  return ''; // 默认返回空字符串
};

const rules = {
  application_id: [{ required: true, message: '请填写申请编号', trigger: 'blur' }], // 新增或修改此行
  data_id: [{ required: true, message: '请填写数据编号', trigger: 'blur' }],
  data_alias: [{ required: true, message: '请填写数据名称', trigger: 'blur' }],
  applicant_name: [{ required: true, message: '请填写申请人姓名', trigger: 'blur' }],
  applicant_user_number: [{ required: true, message: '请填写员工编号', trigger: 'blur' }],
  adm1_name: [{ required: true, message: '请填写一审人员姓名', trigger: 'blur' }],
  adm2_name: [{ required: true, message: '请填写二审人员姓名', trigger: 'blur' }],
  now: [{ required: true, message: '请填写生成水印的时间', trigger: 'blur' }],
  // [新增开始] 新增字段的验证规则 (您可以根据需要设为必填或添加其他规则)
  data_format: [{ message: '请选择数据格式', trigger: 'change' }], // 示例：非必填
  scale: [{ message: '请选择或输入比例尺', trigger: 'change' }], // 示例：非必填
  input_path: [{ message: '请填写输入路径', trigger: 'blur' }], // 示例：非必填
  output_path: [{ message: '请填写输出路径', trigger: 'blur' }], // 示例：非必填
  // [新增结束]
  // copy_data 通常不需要验证规则
};

const initialRequestInformation = {
  application_id: '',
  data_id: '',
  data_alias: '',
  applicant_name: '',
  applicant_user_number: '',
  adm1_name: '',
  adm2_name: '',
  now: '',
  // [新增开始] 为“水印嵌入”功能预留的字段
  data_format: '', // 数据格式
  scale: 'auto',       // 比例尺，默认为“自动”
  input_path: '',  // 输入路径
  output_path: '',  // 输出路径
  copy_data: false // [新增] 复制数据选项，默认为false
  // [新增结束]
};

const requestInformation = reactive({ ...initialRequestInformation });

const get_applications = async () => {
  try {
    const response = await axios.get('http://localhost:5001/api/adm1_get_applications_generate_watermark', {
      params: { page: page.value, pageSize: pageSize.value },
      responseType: 'json'
    });

    if (!response.data || !response.data.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data.msg || '获取记录失败');
      return;
    }

    data.list = response.data.application_data;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error('Error fetching records:', err);
    ElMessage.error('获取记录失败');
  }
};

onMounted(() => {
  get_applications();
});


const openRequestDialog = (row) => {
  Object.assign(requestInformation, {
    application_id: row.id,
    data_id: row.data_id,
    data_alias: row.data_alias,
    applicant_name: row.applicant_name,
    applicant_user_number: row.applicant_user_number,
    adm1_name: row.adm1_name,
    adm2_name: row.adm2_name,
    now: new Date().toLocaleString(),
    // [新增开始] 打开弹窗时，如果需要从row中获取这些新字段的默认值，可以在这里设置
    // 例如: data_format: row.default_data_format || '',
    // 如果没有默认值，则会使用 initialRequestInformation 中的空字符串
    data_format: initialRequestInformation.data_format, // 使用初始默认值
    scale: initialRequestInformation.scale,             // 使用初始默认值
    input_path: initialRequestInformation.input_path,   // 使用初始默认值
    output_path: initialRequestInformation.output_path, // 使用初始默认值
    copy_data: initialRequestInformation.copy_data      // 使用初始默认值
    // [新增结束]
  });
  requestDataVisible.value = true;
};

const resetForm = async () => {
  Object.assign(requestInformation, { ...initialRequestInformation });
  await nextTick();
  requestFormRef.value?.clearValidate();
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('确认关闭？').then(() => {
    done();
    if (dialogType === 'request') {
      resetForm();
    }
  }).catch(() => {});
};

const generate = () => {
  requestFormRef.value.validate((valid) => {
    if (valid) {
      axios.post('http://localhost:5001/api/generate_watermark', requestInformation)
        .then((response) => {
          if (response.data.status) {
            ElMessage.success('生成水印成功');
            get_applications(); // 刷新记录
            requestDataVisible.value = false;
          } else {
            ElMessage.error(response.data.msg || '生成水印失败');
          }
        }).catch((err) => {
          console.error('Error generating watermark:', err);
          ElMessage.error('生成水印失败');
        });
      get_applications()

    } else {
      console.log('表单验证失败');
    }
  });
};

const handleImageError = (scope) => {
  scope.row.qrcode = ''; // 设置默认图片路径
};

</script>

<style>
.qr-code-image {
  width: 50px;
  height: 50px;
}

.view-pagination{
  margin-top: 20px;
}

/* [新增开始] 为弹窗添加自定义样式 */

/* 移除之前自定义的蓝色标题栏样式，因为我们直接修改 el-dialog__header */
/*
.dialog-custom-title-bar {
  background-color: #409EFF; 
  color: white;
  padding: 12px 20px; 
  font-size: 20px; 
  font-weight: bold;
  margin: -30px -20px 30px -20px; 
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
}
*/

/* 针对整个自定义弹窗的样式 */
.custom-watermark-dialog .el-dialog__header {
  /* [修改] 将背景色改为渐变 */
  background-image: linear-gradient(to bottom, #2A6EB3, #58A9FF); /* 深蓝到浅蓝的渐变 */
  padding: 8px 15px;      /* [修改] 进一步减小内边距，使其更紧凑 */
  border-top-left-radius: 4px; 
  border-top-right-radius: 4px;
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: 15px; /* [修改] 进一步减小标题栏和下方内容的间距 */
}

/* 在header中添加“申请使用数据”文字 */
.custom-watermark-dialog .el-dialog__header::before {
  content: "申请使用数据";
  color: white;
  font-size: 16px; /* [修改] 标题字体大小略微调小以适应更紧凑的头部 */
  font-weight: bold;
}

/* 隐藏 Element Plus 默认的 title span */
.custom-watermark-dialog .el-dialog__title {
  display: none; 
}

/* 修改关闭按钮 (×) 的样式 */
.custom-watermark-dialog .el-dialog__headerbtn {
  position: static; 
  height: auto;
  width: auto;
}
.custom-watermark-dialog .el-dialog__headerbtn .el-dialog__close {
  color: red !important; 
  font-size: 16px; /* [修改] 关闭按钮大小与标题字体协调 */
}
.custom-watermark-dialog .el-dialog__headerbtn .el-dialog__close:hover {
  color: darkred !important; 
}


/* 调整 Element Plus 分割线内文字的样式 */
.custom-watermark-dialog .section-divider .el-divider__text {
  font-size: 14px; /* [修改] 分区标题字体大小略微调小 */
  font-weight: bold;
  color: #303133; 
  padding: 0 10px; /* [修改] 减小内边距 */
}
.custom-watermark-dialog .el-divider--horizontal{
  margin: 15px 0; /* [修改] 减小分割线上下的间距 */
}

/* 调整表单标签字体大小和对齐 */
.custom-watermark-dialog .el-form-item__label {
  font-size: 13px;
  color: #606266; 
  padding-right: 8px; /* [修改] 减小标签和输入框之间的间距 */
  line-height: 32px; 
  height: 32px; /* [新增] 确保标签高度与输入框一致 */
  display: inline-flex; /* [新增] 使用flex布局进行垂直居中 */
  align-items: center; /* [新增] 垂直居中标签内文字（包括星号）*/
}

/* 表单项的垂直间距 */
.custom-watermark-dialog .el-form-item {
  margin-bottom: 10px; /* [修改] 进一步减小行间距 */
}

/* [删除开始] 移除对输入框和选择框固定宽度的限制 (这个之前已经注释掉了，保持不变) */
/*
.custom-watermark-dialog .el-input,
.custom-watermark-dialog .el-select {
  width: 220px; 
}
*/
/* [删除结束] */


.custom-watermark-dialog .el-input__inner,
.custom-watermark-dialog .el-select .el-input__inner,
.custom-watermark-dialog .el-textarea__inner {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-size: 13px;
  height: 32px;
  line-height: 32px;
  padding-right: 140px !important; /* 修改：增加右内边距，为错误提示和图标预留空间 */
}

/* 针对选择框的下拉箭头等也需要调整一下大小和对齐 */
.custom-watermark-dialog .el-select .el-input .el-select__caret {
  font-size: 13px; /* [修改] 调整下拉箭头大小 */
}


/* 对于包含按钮的行，确保输入框能正确填充 */
/* .custom-watermark-dialog .el-form-item .el-input { */
   /* width: auto; */ 
/* } */

/* 给整个对话框添加暗蓝色边框 */
.custom-watermark-dialog .el-dialog {
  border: 2px solid #2A6EB3; /* 暗蓝色边框 */
  border-radius: 6px;
  overflow: hidden; /* 确保边框圆角正常显示 */
}

/* 调整按钮之间的间距 */
.custom-watermark-dialog .el-form-item:last-child .el-button + .el-button {
  margin-left: 80px; /* 增加按钮之间的间距 */
}

/* 调整按钮组的样式 (通常是最后一个表单项) */
.custom-watermark-dialog .el-form-item:last-child {
  margin-bottom: 0; /* 最后一个表单项通常不需要底部外边距 */
  margin-top: 20px; /* 修改：减小与上方表单的距离，比如从 40px 改为 20px */
  text-align: center; /* 按钮居中显示 */
}

/* 调整按钮之间的间距 */
.custom-watermark-dialog .el-form-item:last-child .el-button + .el-button {
  margin-left: 120px; /* 修改：增加按钮之间的间距，比如从 80px 改为 120px，让重置按钮更靠右 */
}

/* 调整浏览按钮的样式，使其更紧凑 */
.custom-watermark-dialog .el-form-item .el-button--small {
    padding: 5px 10px; /* [修改] 针对浏览按钮这种small类型的按钮进一步减小padding */
    font-size: 13px; 
}

/* [新增] 调整复选框的样式 */
.custom-watermark-dialog .el-checkbox__label {
  font-size: 13px; /* [修改] 复选框标签文字大小从 12px 增加到 13px */
  padding-left: 8px; /* [修改] 调整复选框与文字间距 */
}
.custom-watermark-dialog .el-checkbox__inner {
  width: 15px; /* [修改] 适当调整复选框大小 */
  height: 15px;
}
.custom-watermark-dialog .el-checkbox__inner::after { /* 调整勾号大小和位置 */
    height: 8px;
    left: 4px; /* 可能需要微调 */
    top: 1px;  /* 可能需要微调 */
    width: 4px;/* 可能需要微调 */
}

/* [新增结束] */

/* 调整表单验证提示的位置和样式 */
.custom-watermark-dialog .el-form-item__error {
  position: absolute;
  top: 50%; /* 垂直居中 */
  transform: translateY(-50%); /* 精确垂直居中 */
  right: 40px; /* 修改：定位到输入框内部右侧，验证图标的左边 */
  font-size: 12px;
  line-height: 1; /* 确保单行文字的行高 */
  color: #F56C6C;
  z-index: 1; /* 确保在输入内容之上 */
  background-color: transparent;
  padding: 0 2px;
  pointer-events: none; /* 错误信息不捕获鼠标事件，以免干扰输入 */

  /* 处理可能过长的错误信息 */
  max-width: 95px; /* 修改：最大宽度，避免遮挡验证图标或溢出过多 */
  white-space: nowrap; /* 不换行 */
  overflow: hidden; /* 超出部分隐藏 */
  text-overflow: ellipsis; /* 超出部分显示省略号 */
}

/* 调整输入框和选择框的样式，为右侧的错误提示和状态图标留出空间 */
.custom-watermark-dialog .el-input__inner,
.custom-watermark-dialog .el-select .el-input__inner {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-size: 13px;
  height: 32px;
  line-height: 32px;
  /* 修改：显著增加右内边距，以容纳错误提示文字和状态图标 */
  /* 这个值需要根据您最长的错误提示和图标宽度来调整 */
  /* 假设状态图标约20-25px宽，错误提示最长如“请填写一审人员姓名”约100-120px */
  padding-right: 160px; /* 示例值，请根据实际情况调整 */
}


/* 调整按钮组的样式 (通常是最后一个表单项) */
.custom-watermark-dialog .el-form-item:last-child {
  margin-bottom: 0;
  margin-top: 10px; /* 修改：减小与上方表单的距离，例如从 20px 改为 10px */
  text-align: center;
}

/* 调整按钮之间的间距 */
.custom-watermark-dialog .el-form-item:last-child .el-button + .el-button {
  margin-left: 150px; /* 修改：进一步增加按钮之间的间距，例如从 120px 改为 150px */
}

/* 确保输入框内部有足够空间显示错误信息 */
.custom-watermark-dialog .el-input__inner {
  padding-right: 30px; /* 为错误信息预留空间 */
}
</style>
