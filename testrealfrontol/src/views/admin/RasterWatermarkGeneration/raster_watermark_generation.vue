<!-- src/views/admin/Watermark Generation/raster_watermark_generation.vue -->
<!-- 栅格数据水印生成界面 -->

<template>
    <div>
      <!-- 水印生成申请表格 -->
      <el-table :data="data.list" border>
        <el-table-column prop="id" :label="$t('rasterWmGen.colApplicationId')" width="85" />
        <el-table-column prop="data_alias" :label="$t('rasterWmGen.colDataName')" width="85"/>
        <el-table-column prop="data_id" :label="$t('rasterWmGen.colRasterDataId')" width="110"/>
        <el-table-column prop="applicant_user_number" :label="$t('rasterWmGen.colApplicantNo')" width="100"/>
        <el-table-column prop="applicant_name" :label="$t('rasterWmGen.colApplicantName')" width="100"/>
        <el-table-column prop="adm1_name" :label="$t('rasterWmGen.colAdm1Name')" width="120"/>
        <el-table-column prop="adm2_name" :label="$t('rasterWmGen.colAdm2Name')" width="120"/>

        <el-table-column :label="$t('rasterWmGen.colFirstStatus')" width="100">
          <template v-slot="scope">
            {{ getStatusText(scope.row.first_statu) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('rasterWmGen.colSecondStatus')" width="100">
          <template v-slot="scope">
            <div v-if="!scope.row.first_statu">
              {{ getStatusText(null) }}
            </div>
            <div v-else>
              {{ getStatusText(scope.row.second_statu) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('rasterWmGen.colWatermark')">
          <template #default="scope">
            <el-image class="qr-code-image"
              :src="scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : ''"
              :preview-src-list="[scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : '']"
              fit="cover"
              style="width: 50px; height: 50px;"
            />
          </template>
        </el-table-column>

        <el-table-column :label="$t('rasterWmGen.colAction')" width="122.5">
          <template v-slot="scope">
            <el-button size="small" type="primary" @click="openRequestDialog(scope.row)">{{ $t('rasterWmGen.generateWatermark') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页组件 -->
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

    <!-- 水印生成表单弹窗 -->
    <el-dialog
      v-model="requestDataVisible"
      width="550px"
      :before-close="(done)=>handleClose('request',done)"
      :show-close="true"
      :close-on-click-modal="false"
      class="custom-watermark-dialog"
      :title="$t('rasterWmGen.requestDialogTitle')"
    >
      <el-form ref="requestFormRef" :model="requestInformation" status-icon :rules="rules" label-position="left" label-width="90px">
        <el-divider content-position="left" class="section-divider">{{ $t('rasterWmGen.sectionWatermarkInfo') }}</el-divider>
        <el-form-item :label="$t('rasterWmGen.formApplicationId')" prop="application_id" required>
          <el-input v-model="requestInformation.application_id" :placeholder="$t('rasterWmGen.placeholderFillApplicationId')" disabled/>
        </el-form-item>
        <el-form-item :label="$t('rasterWmGen.formDataId')" prop="data_id">
          <el-input v-model="requestInformation.data_id" :placeholder="$t('rasterWmGen.placeholderFill')" disabled/>
        </el-form-item>
        <el-form-item :label="$t('rasterWmGen.formDataName')" prop="data_alias">
          <el-input v-model="requestInformation.data_alias" :placeholder="$t('rasterWmGen.placeholderFill')" disabled/>
        </el-form-item>
        <el-form-item :label="$t('rasterWmGen.formApplicantName')" prop="applicant_name">
          <el-input v-model="requestInformation.applicant_name" :placeholder="$t('rasterWmGen.placeholderFill')" disabled/>
        </el-form-item>
        <el-form-item :label="$t('rasterWmGen.formEmployeeNo')" prop="applicant_user_number">
          <el-input v-model="requestInformation.applicant_user_number" :placeholder="$t('rasterWmGen.placeholderFill')" disabled/>
        </el-form-item>
        <el-form-item :label="$t('rasterWmGen.formAdm1')" prop="adm1_name">
          <el-input v-model="requestInformation.adm1_name" :placeholder="$t('rasterWmGen.placeholderFill')" disabled/>
        </el-form-item>
        <el-form-item :label="$t('rasterWmGen.formAdm2')" prop="adm2_name">
          <el-input v-model="requestInformation.adm2_name" :placeholder="$t('rasterWmGen.placeholderFill')" disabled/>
        </el-form-item>
        <el-form-item :label="$t('rasterWmGen.formGenerateTime')" prop="now">
          <el-input v-model="requestInformation.now" :placeholder="$t('rasterWmGen.placeholderAutoFill')" disabled/>
        </el-form-item>

        <el-divider content-position="left" class="section-divider">{{ $t('rasterWmGen.sectionDataOptions') }}</el-divider>
        <el-form-item :label="$t('rasterWmGen.formDataType')" prop="data_format">
          <el-select v-model="requestInformation.data_format" :placeholder="$t('rasterWmGen.placeholderSelect')" style="width: 100%;">
            <!-- 栅格数据格式选项 -->
            <el-option label="GeoTIFF" value="geotiff"></el-option>
            <el-option label="JPEG" value="jpeg"></el-option>
            <el-option label="PNG" value="png"></el-option>
            <el-option label="Grid" value="grid"></el-option>
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('rasterWmGen.formResolution')" prop="resolution">
          <el-select v-model="requestInformation.resolution" :placeholder="$t('rasterWmGen.placeholderSelect')" style="width: 100%;">
            <el-option :label="$t('rasterWmGen.resolutionAuto')" value="auto"></el-option>
            <el-option :label="$t('rasterWmGen.resolution10m')" value="10m"></el-option>
            <el-option :label="$t('rasterWmGen.resolution30m')" value="30m"></el-option>
          </el-select>
        </el-form-item>

        <el-divider content-position="left" class="section-divider">{{ $t('rasterWmGen.sectionPaths') }}</el-divider>
        <el-form-item :label="$t('rasterWmGen.formInputPath')" prop="input_path">
          <div style="display: flex; align-items: center; width: 100%;">
            <el-input v-model="requestInformation.input_path" :placeholder="$t('rasterWmGen.placeholderFill')" style="flex-grow: 1; margin-right: 10px;"/>
            <el-button type="primary" size="small">{{ $t('rasterWmGen.browse') }}</el-button>
          </div>
        </el-form-item>

        <el-form-item :label="$t('rasterWmGen.formOutputPath')" prop="output_path">
          <div style="display: flex; align-items: center; width: 100%;">
            <el-input v-model="requestInformation.output_path" :placeholder="$t('rasterWmGen.placeholderFill')" style="flex-grow: 1; margin-right: 10px;"/>
            <el-button type="primary" size="small">{{ $t('rasterWmGen.browse') }}</el-button>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="generate" :loading="generating">{{ $t('rasterWmGen.confirmGenerate') }}</el-button>
          <el-button @click="resetForm">{{ $t('rasterWmGen.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </template>

  <script setup>
  import { reactive, ref, onMounted, watch, nextTick } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { ElMessage, ElMessageBox } from 'element-plus';
  import { getRasterApplicationsGenerateWatermark, generateRasterWatermark } from '@/api/watermark';

  const { t } = useI18n();

  const data = reactive({ list: [] });
  const page = ref(1);
  const pageSize = ref(10);
  const total = ref(0);
  const requestDataVisible = ref(false);
  const requestFormRef = ref(null);
  const generating = ref(false);


  watch(page, (newValue, oldValue) => {
    if (oldValue !== newValue) {
      get_applications();
    }
  });

  const pageChanged = (newPage) => {
    page.value = newPage;
  };

  const getStatusText = (status) => {
    if (status === true) return t('rasterWmGen.statusPassed');
    if (status === false) return t('rasterWmGen.statusRejected');
    if (status === null) return t('rasterWmGen.statusPending');
    return ''; // 默认返回空字符串
  };

  const rules = {
    application_id: [{ required: true, message: t('rasterWmGen.ruleFillApplicationId'), trigger: 'blur' }],
    data_id: [{ required: true, message: t('rasterWmGen.ruleFillDataId'), trigger: 'blur' }],
    data_alias: [{ required: true, message: t('rasterWmGen.ruleFillDataName'), trigger: 'blur' }],
    applicant_name: [{ required: true, message: t('rasterWmGen.ruleFillApplicantName'), trigger: 'blur' }],
    applicant_user_number: [{ required: true, message: t('rasterWmGen.ruleFillEmployeeNo'), trigger: 'blur' }],
    adm1_name: [{ required: true, message: t('rasterWmGen.ruleFillAdm1Name'), trigger: 'blur' }],
    adm2_name: [{ required: true, message: t('rasterWmGen.ruleFillAdm2Name'), trigger: 'blur' }],
    now: [{ required: true, message: t('rasterWmGen.ruleFillGenerateTime'), trigger: 'blur' }],
    data_format: [{ message: t('rasterWmGen.ruleSelectDataType'), trigger: 'change' }],
    resolution: [{ message: t('rasterWmGen.ruleSelectResolution'), trigger: 'change' }],
    input_path: [{ message: t('rasterWmGen.ruleFillInputPath'), trigger: 'blur' }],
    output_path: [{ message: t('rasterWmGen.ruleFillOutputPath'), trigger: 'blur' }],
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
    // 栅格数据特有的字段
    data_format: '',
    resolution: 'auto',
    input_path: '',
    output_path: '',
  };

  const requestInformation = reactive({ ...initialRequestInformation });

  const get_applications = async () => {
    try {
      // 调用栅格数据专用的API端点
      const response = await getRasterApplicationsGenerateWatermark({ page: page.value, pageSize: pageSize.value });

      if (!response.data || !response.data.status) {
        data.list = [];
        total.value = 0;
        ElMessage.error(response.data.msg || t('rasterWmGen.fetchFailed'));
        return;
      }

      data.list = response.data.application_data;
      total.value = response.data.pages.total;
    } catch (err) {
      console.error('Error fetching records:', err);
      ElMessage.error(t('rasterWmGen.fetchFailed'));
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
      // 使用初始默认值
      data_format: initialRequestInformation.data_format,
      resolution: initialRequestInformation.resolution,
      input_path: initialRequestInformation.input_path,
      output_path: initialRequestInformation.output_path,
    });
    requestDataVisible.value = true;
  };

  const resetForm = async () => {
    Object.assign(requestInformation, { ...initialRequestInformation });
    await nextTick();
    requestFormRef.value?.clearValidate();
  };

  const handleClose = (dialogType, done) => {
    ElMessageBox.confirm(t('rasterWmGen.confirmClose')).then(() => {
      done();
      if (dialogType === 'request') {
        resetForm();
      }
    }).catch(() => {});
  };

  const generate = () => {
    requestFormRef.value.validate(async (valid) => {
      if (!valid) return;
      generating.value = true;
      try {
        const response = await generateRasterWatermark(requestInformation);
        if (response.data.status) {
          ElMessage.success(t('rasterWmGen.generateSuccess'));
          get_applications();
          requestDataVisible.value = false;
        } else {
          ElMessage.error(response.data.msg || t('rasterWmGen.generateFailed'));
        }
      } catch (err) {
        ElMessage.error(t('rasterWmGen.generateFailed'));
      } finally {
        generating.value = false;
      }
    });
  };

  </script>

  <style scoped>
  /* 样式与矢量数据代码保持一致，确保外观统一 */
  .qr-code-image {
    width: 50px;
    height: 50px;
  }

  .view-pagination{
    margin-top: 20px;
  }

  .custom-watermark-dialog .el-dialog__header {
    background-image: linear-gradient(to bottom, #2A6EB3, #58A9FF);
    padding: 8px 15px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
  }

  .custom-watermark-dialog .el-dialog__title {
    color: white;
    font-size: 16px;
    font-weight: bold;
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
  .custom-watermark-dialog .el-divider--horizontal{
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

  .custom-watermark-dialog .el-select .el-input .el-select__caret {
    font-size: 13px;
  }

  .custom-watermark-dialog .el-dialog {
    border: 2px solid #2A6EB3;
    border-radius: 6px;
    overflow: hidden;
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
    color: #F56C6C;
    z-index: 1;
    background-color: transparent;
    padding: 0 2px;
    pointer-events: none;
    max-width: 95px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .custom-watermark-dialog .el-input__inner,
  .custom-watermark-dialog .el-select .el-input__inner {
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    font-size: 13px;
    height: 32px;
    line-height: 32px;
    padding-right: 30px;
  }

  .custom-watermark-dialog .el-form-item:last-child {
    margin-bottom: 0;
    margin-top: 10px;
    text-align: center;
  }

  .custom-watermark-dialog .el-form-item:last-child .el-button + .el-button {
    margin-left: 150px;
  }
  </style>
