<template>
  <div class="dual-channel-approval">
    <!-- 页面标题和统计 -->
    <el-card class="header-card" shadow="never">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">{{ $t('approval.dualChannelTitle') }}</h1>
          <p class="page-subtitle">{{ $t('approval.dualChannelSubtitle') }}</p>
        </div>
        <div class="stats-section">
          <div class="stat-item">
            <div class="stat-number">{{ pendingVectorCount }}</div>
            <div class="stat-label">{{ $t('approval.pendingVector') }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">{{ pendingRasterCount }}</div>
            <div class="stat-label">{{ $t('approval.pendingRaster') }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">{{ totalProcessed }}</div>
            <div class="stat-label">{{ $t('approval.processed') }}</div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 数据类型选择和筛选 -->
    <el-card class="filter-card" shadow="hover">
      <div class="filter-content">
        <el-radio-group v-model="activeDataType" size="large" class="data-type-selector">
          <el-radio-button value="vector">
            <el-icon><Location /></el-icon>
            {{ $t('approval.vectorData') }} ({{ vectorApplications.length }})
          </el-radio-button>
          <el-radio-button value="raster">
            <el-icon><Picture /></el-icon>
            {{ $t('approval.rasterData') }} ({{ rasterApplications.length }})
          </el-radio-button>
        </el-radio-group>

        <div class="filter-controls">
          <el-input
            v-model="searchKeyword"
            :placeholder="$t('approval.searchApplicantPlaceholder')"
            style="width: 300px"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-select v-model="statusFilter" :placeholder="$t('approval.reviewStatus')" style="width: 120px">
            <el-option :label="$t('approval.all')" value="" />
            <el-option :label="$t('approval.pendingFirst')" value="pending_first" />
            <el-option :label="$t('approval.pendingSecond')" value="pending_second" />
            <el-option :label="$t('approval.approved')" value="approved" />
            <el-option :label="$t('approval.rejected')" value="rejected" />
          </el-select>
        </div>
      </div>
    </el-card>

    <!-- 数据列表 -->
    <el-card class="data-list-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h3 class="card-title">
            <el-icon><component :is="activeDataType === 'vector' ? 'Location' : 'Picture'" /></el-icon>
            {{ activeDataType === 'vector' ? $t('approval.vectorData') : $t('approval.rasterData') }} {{ $t('approval.reviewList') }}
          </h3>
          <div class="header-actions">
            <el-button type="primary" :icon="Refresh" @click="refreshData">{{ $t('approval.refresh') }}</el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="paginatedApplications"
        border
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column type="expand">
          <template #default="props">
            <div class="application-detail">
              <el-descriptions :column="2" border>
                <el-descriptions-item :label="$t('approval.applyId')">{{ props.row.id }}</el-descriptions-item>
                <el-descriptions-item :label="$t('approval.applyTime')">{{ props.row.application_time }}</el-descriptions-item>
                <el-descriptions-item :label="$t('approval.dataType')">{{ getDataTypeText(props.row.data_type) }}</el-descriptions-item>
                <el-descriptions-item :label="$t('approval.dataSize')">{{ props.row.data_size || $t('approval.unknown') }}</el-descriptions-item>
                <el-descriptions-item :label="$t('approval.applyReason')" :span="2">{{ props.row.reason }}</el-descriptions-item>
                <el-descriptions-item :label="$t('approval.purpose')" :span="2">{{ props.row.purpose || $t('approval.notFilled') }}</el-descriptions-item>
              </el-descriptions>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="id" :label="$t('approval.applyId')" width="100" />
        <el-table-column prop="data_alias" :label="$t('approval.dataName')" min-width="150" />
        <el-table-column prop="data_id" :label="$t('approval.dataId')" width="120" />
        <el-table-column prop="applicant_name" :label="$t('approval.applicant')" width="120" />
        <el-table-column prop="applicant_user_number" :label="$t('approval.userId')" width="100" />

        <el-table-column :label="$t('approval.reviewStatus')" width="120" align="center">
          <template #default="scope">
            <el-tag
              :type="getStatusType(scope.row)"
              size="large"
              effect="dark"
            >
              {{ getStatusText(scope.row) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="$t('approval.firstReviewInfo')" width="150" align="center">
          <template #default="scope">
            <div class="review-info">
              <div class="review-status" :class="getFirstReviewClass(scope.row)">
                {{ getFirstReviewText(scope.row) }}
              </div>
              <div class="review-time" v-if="scope.row.first_review_time">
                {{ formatTime(scope.row.first_review_time) }}
              </div>
              <div class="reviewer" v-if="scope.row.first_reviewer">
                {{ scope.row.first_reviewer }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('approval.secondReviewInfo')" width="150" align="center">
          <template #default="scope">
            <div class="review-info">
              <div class="review-status" :class="getSecondReviewClass(scope.row)">
                {{ getSecondReviewText(scope.row) }}
              </div>
              <div class="review-time" v-if="scope.row.second_review_time">
                {{ formatTime(scope.row.second_review_time) }}
              </div>
              <div class="reviewer" v-if="scope.row.second_reviewer">
                {{ scope.row.second_reviewer }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('approval.operation')" width="180" align="center" fixed="right">
          <template #default="scope">
            <div class="action-buttons">
              <el-button
                v-if="canFirstReview(scope.row)"
                type="success"
                size="small"
                :icon="Check"
                @click="handleFirstApprove(scope.row)"
              >
                {{ $t('approval.firstReviewPass') }}
              </el-button>
              <el-button
                v-if="canFirstReview(scope.row)"
                type="danger"
                size="small"
                :icon="Close"
                @click="handleFirstReject(scope.row)"
              >
                {{ $t('approval.firstReviewReject') }}
              </el-button>
              <el-button
                v-if="canSecondReview(scope.row)"
                type="success"
                size="small"
                :icon="Check"
                @click="handleSecondApprove(scope.row)"
              >
                {{ $t('approval.secondReviewPass') }}
              </el-button>
              <el-button
                v-if="canSecondReview(scope.row)"
                type="danger"
                size="small"
                :icon="Close"
                @click="handleSecondReject(scope.row)"
              >
                {{ $t('approval.secondReviewReject') }}
              </el-button>
              <el-button
                v-if="canAdditionalReview(scope.row)"
                type="warning"
                size="small"
                @click="handleAdditionalReview(scope.row)"
              >
                {{ $t('approval.additionalReview') }}
              </el-button>
              <el-button
                v-if="scope.row.status === 'approved' || scope.row.status === 'adm2_approved'"
                type="info"
                size="small"
                :icon="View"
                @click="viewApplicationDetail(scope.row)"
              >
                {{ $t('approval.viewDetail') }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalCount"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { useI18n } from 'vue-i18n'
import axios from '@/utils/Axios'
import { useUserStore } from '@/stores/userStore.js'
import { Location, Picture, Search, Check, Close, View, Refresh } from '@element-plus/icons-vue'

const { t } = useI18n()

const userStore = useUserStore()

// 数据状态
const loading = ref(false)
const activeDataType = ref('vector') // vector 或 raster
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// 统计数据
const pendingVectorCount = ref(0)
const pendingRasterCount = ref(0)
const totalProcessed = ref(0)

// 申请数据
const vectorApplications = ref([])
const rasterApplications = ref([])

// 计算属性
const filteredApplications = computed(() => {
  const sourceData = activeDataType.value === 'vector' ? vectorApplications.value : rasterApplications.value

  let filtered = sourceData.filter(item => {
    // 搜索筛选
    const keyword = searchKeyword.value.toLowerCase()
    const matchesSearch = !keyword ||
      item.applicant_name.toLowerCase().includes(keyword) ||
      item.data_alias.toLowerCase().includes(keyword) ||
      item.id.toString().includes(keyword) ||
      item.applicant_user_number.toLowerCase().includes(keyword)

    // 状态筛选
    const matchesStatus = !statusFilter.value || getStatusValue(item) === statusFilter.value

    return matchesSearch && matchesStatus
  })

  return filtered
})

const totalCount = computed(() => filteredApplications.value.length)

// 分页后的数据
const paginatedApplications = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredApplications.value.slice(start, end)
})

// 方法定义
const getDataTypeText = (type) => {
  const typeMap = {
    'vector': t('approval.vectorData'),
    'raster': t('approval.rasterData'),
    'shp': t('approval.vectorData'),
    'raster_data': t('approval.rasterData')
  }
  return typeMap[type] || type
}

const getStatusValue = (row) => {
  if (row.adm3_statu === false) return 'rejected'
  if (row.status === 'pending') return 'pending_first'
  if (row.status === 'adm1_approved') return 'pending_second'
  if (row.status === 'adm2_approved') return 'approved'
  if (row.status === 'adm1_rejected' || row.status === 'adm2_rejected') return 'rejected'
  return row.status
}

const getStatusType = (row) => {
  const status = getStatusValue(row)
  const typeMap = {
    'pending_first': 'warning',
    'pending_second': '',
    'approved': 'success',
    'rejected': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (row) => {
  const status = getStatusValue(row)
  const textMap = {
    'pending_first': t('approval.pendingFirst'),
    'pending_second': t('approval.pendingSecond'),
    'approved': t('approval.approved'),
    'rejected': t('approval.rejected')
  }
  return textMap[status] || status
}

const getFirstReviewClass = (row) => {
  if (row.status === 'pending') return 'pending'
  if (row.status === 'adm1_approved') return 'approved'
  if (row.status === 'adm1_rejected') return 'rejected'
  if (row.status === 'adm2_approved' || row.status === 'adm2_rejected') return 'approved'
  return ''
}

const getFirstReviewText = (row) => {
  if (row.status === 'pending') return t('approval.pending')
  if (row.status === 'adm1_approved') return t('approval.approved')
  if (row.status === 'adm1_rejected') return t('approval.rejected')
  if (row.status === 'adm2_approved' || row.status === 'adm2_rejected') return t('approval.approved')
  return t('approval.notStarted')
}

const getSecondReviewClass = (row) => {
  if (row.status === 'adm2_approved') return 'approved'
  if (row.status === 'adm2_rejected') return 'rejected'
  if (row.status === 'adm1_approved') return 'pending'
  return ''
}

const getSecondReviewText = (row) => {
  if (row.status === 'adm2_approved') return t('approval.approved')
  if (row.status === 'adm2_rejected') return t('approval.rejected')
  if (row.status === 'adm1_approved') return t('approval.pending')
  return t('approval.notStarted')
}

const currentAdminRole = computed(() => {
  const n = (userStore.userNumber || '').toString().toLowerCase()
  if (n === 'adm1' || n === 'admin1' || n === '22200214135') return 'adm1'
  if (n === 'adm2' || n === 'admin2' || n === '33300214135') return 'adm2'
  if (n === 'adm3' || n === 'admin3' || n === '44400214135') return 'adm3'
  return ''
})

const canFirstReview = (row) => {
  return currentAdminRole.value === 'adm1' && row.status === 'pending'
}

const canSecondReview = (row) => {
  return currentAdminRole.value === 'adm2' && row.status === 'adm1_approved'
}

const canAdditionalReview = (row) => {
  return ['adm1', 'adm2', 'adm3'].includes(currentAdminRole.value) && row.status === 'adm2_approved'
}

const formatTime = (time) => {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN')
}

// 审核操作
const handleFirstApprove = async (row) => {
  try {
    await ElMessageBox.confirm(t('approval.confirmFirstApprove'), t('approval.firstReviewApproval'), {
      confirmButtonText: t('approval.approve'),
      cancelButtonText: t('approval.cancel'),
      type: 'info'
    })

    const response = await axios.post(`/api/adm1_pass`, {
      id: row.id,
      user_name: userStore.userName,
      user_number: userStore.userNumber
    })

    if (response.data.status) {
      ElMessage.success(t('approval.firstApproveSuccess'))
      await refreshData()
    } else {
      ElMessage.error(response.data.msg || t('approval.reviewFailed'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('approval.reviewOperationFailed'))
    }
  }
}

const handleFirstReject = async (row) => {
  try {
    const { value: reason } = await ElMessageBox.prompt(t('approval.enterRejectReason'), t('approval.firstRejectTitle'), {
      confirmButtonText: t('approval.reject'),
      cancelButtonText: t('approval.cancel'),
      inputPattern: /^[\s\S]{5,}$/,
      inputErrorMessage: t('approval.rejectReasonMinLength')
    })

    const response = await axios.post(`/api/adm1_fail`, {
      id: row.id,
      user_name: userStore.userName,
      user_number: userStore.userNumber,
      reason: reason
    })

    if (response.data.status) {
      ElMessage.success(t('approval.firstRejectSuccess'))
      await refreshData()
    } else {
      ElMessage.error(response.data.msg || t('approval.rejectFailed'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('approval.rejectOperationFailed'))
    }
  }
}

const handleSecondApprove = async (row) => {
  try {
    await ElMessageBox.confirm(t('approval.confirmSecondApprove'), t('approval.secondReviewApproval'), {
      confirmButtonText: t('approval.approve'),
      cancelButtonText: t('approval.cancel'),
      type: 'info'
    })

    const loadingInstance = ElLoading.service({
      lock: true,
      text: t('approval.processing'),
      background: 'rgba(0, 0, 0, 0.7)',
    })

    try {
      const response = await axios.post(`/api/adm2_pass`, {
        id: row.id,
        user_name: userStore.userName,
        user_number: userStore.userNumber
      })

      if (response.data.status) {
        ElMessage.success(t('approval.reviewPassed'))
        await refreshData()
      } else {
        ElMessage.error(response.data.msg || t('approval.reviewFailed'))
      }
    } finally {
      loadingInstance.close()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('approval.reviewOperationFailed'))
    }
  }
}

const handleSecondReject = async (row) => {
  try {
    const { value: reason } = await ElMessageBox.prompt(t('approval.enterRejectReason'), t('approval.secondRejectTitle'), {
      confirmButtonText: t('approval.reject'),
      cancelButtonText: t('approval.cancel'),
      inputPattern: /^[\s\S]{5,}$/,
      inputErrorMessage: t('approval.rejectReasonMinLength')
    })

    const response = await axios.post(`/api/adm2_fail`, {
      id: row.id,
      user_name: userStore.userName,
      user_number: userStore.userNumber,
      reason: reason
    })

    if (response.data.status) {
      ElMessage.success(t('approval.secondRejectSuccess'))
      await refreshData()
    } else {
      ElMessage.error(response.data.msg || t('approval.rejectFailed'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('approval.rejectOperationFailed'))
    }
  }
}

const handleAdditionalReview = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt(t('approval.enterAdditionalReviewOpinion'), t('approval.additionalReviewTitle'), {
      confirmButtonText: t('approval.submitReject'),
      cancelButtonText: t('approval.cancel'),
      inputPattern: /^[\s\S]{5,}$/,
      inputErrorMessage: t('approval.additionalReviewMinLength')
    })

    const response = await axios.post(`/api/adm3_additional_review`, {
      id: row.id,
      statu: false,
      reason: value,
      user_name: userStore.userName,
      user_number: userStore.userNumber
    })

    if (response.data?.status) {
      ElMessage.success(t('approval.additionalReviewSubmitted'))
      await refreshData()
    } else {
      ElMessage.error(response.data?.msg || t('approval.additionalReviewFailed'))
    }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(t('approval.additionalReviewFailed'))
  }
}

const viewApplicationDetail = (row) => {
  // 查看申请详情
  console.log('查看申请详情:', row)
}

// 数据获取
const fetchVectorApplications = async () => {
  try {
    loading.value = true
    const response = await axios.get(`/api/adm1_get_shp_applications`, {
      params: { page: 1, pageSize: 100 }
    })

    if (response.data && response.data.status) {
      vectorApplications.value = response.data.application_data || []
      pendingVectorCount.value = vectorApplications.value.filter(item =>
        item.status === 'pending' || item.status === 'adm1_approved'
      ).length
    }
  } catch (error) {
    ElMessage.error(t('approval.fetchVectorFailed'))
    console.error('获取矢量数据申请失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchRasterApplications = async () => {
  try {
    loading.value = true
    const response = await axios.get(`/api/adm1_get_raster_applications`, {
      params: { page: 1, pageSize: 100 }
    })

    if (response.data && response.data.status) {
      rasterApplications.value = response.data.application_data || []
      pendingRasterCount.value = rasterApplications.value.filter(item =>
        item.status === 'pending' || item.status === 'adm1_approved'
      ).length
    }
  } catch (error) {
    ElMessage.error(t('approval.fetchRasterFailed'))
    console.error('获取遥感数据申请失败:', error)
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await Promise.all([
    fetchVectorApplications(),
    fetchRasterApplications()
  ])
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

// 监听数据类型切换
watch(activeDataType, () => {
  currentPage.value = 1
  searchKeyword.value = ''
  statusFilter.value = ''
})

// 生命周期
onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.dual-channel-approval {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 84px);
}

/* 头部卡片 - 使用普通div而非el-card */
.header-card {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
  border: none !important;
  border-radius: 12px;
  color: white !important;
}

.header-card :deep(.el-card__body) {
  background: transparent !important;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
}

.title-section .page-title {
  font-size: 26px;
  font-weight: bold;
  margin: 0;
  color: #ffffff !important;
}

.title-section .page-subtitle {
  font-size: 14px;
  color: #e0e7ff !important;
  margin: 8px 0 0 0;
}

.stats-section {
  display: flex;
  gap: 40px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 30px;
  font-weight: bold;
  color: #ffffff !important;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #e0e7ff !important;
}

/* 筛选卡片 */
.filter-card {
  margin-bottom: 20px;
}

.filter-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-type-selector {
  display: flex;
  gap: 20px;
}

.filter-controls {
  display: flex;
  gap: 16px;
  align-items: center;
}

/* 数据列表卡片 */
.data-list-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* 申请详情 */
.application-detail {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

/* 审核信息 */
.review-info {
  text-align: center;
}

.review-status {
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin-bottom: 4px;
}

.review-status.pending {
  background: #fdf6ec;
  color: #e6a23c;
}

.review-status.approved {
  background: #f0f9ff;
  color: #67c23a;
}

.review-status.rejected {
  background: #fef0f0;
  color: #f56c6c;
}

.review-time {
  font-size: 11px;
  color: #999;
  margin-bottom: 2px;
}

.reviewer {
  font-size: 11px;
  color: #666;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.action-buttons .el-button {
  margin: 0;
}

/* 分页 */
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .header-content {
    flex-direction: column;
    gap: 20px;
    text-align: center;
  }

  .filter-content {
    flex-direction: column;
    gap: 16px;
  }

  .filter-controls {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .dual-channel-approval {
    padding: 12px;
  }

  .stats-section {
    gap: 20px;
  }

  .stat-number {
    font-size: 24px;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
