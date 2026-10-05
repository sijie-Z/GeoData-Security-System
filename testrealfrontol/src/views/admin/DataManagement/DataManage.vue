<template>
  <div class="data-manage-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('adminDataManage.title') }}</h1>
      <p class="page-description">{{ $t('adminDataManage.description') }}</p>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="data-tabs">
      <el-tab-pane :label="$t('adminDataManage.vectorData')" name="vector" />
      <el-tab-pane :label="$t('adminDataManage.rasterData')" name="raster" />
    </el-tabs>

    <!-- 搜索栏 -->
    <div class="toolbar">
      <el-input v-model="keyword" :placeholder="$t('adminDataManage.searchPlaceholder')" clearable
        @keyup.enter="fetchData" style="width: 300px" :prefix-icon="Search" />
      <el-button type="primary" @click="fetchData">{{ $t('adminDataManage.search') }}</el-button>
    </div>

    <!-- 数据表格 -->
    <el-table :data="dataList" v-loading="loading" stripe style="width: 100%"
      :empty-text="$t('adminDataManage.noData')">
      <el-table-column prop="data_id" label="ID" width="60" />
      <el-table-column prop="data_alias" :label="$t('adminDataManage.dataName')" min-width="150" show-overflow-tooltip />
      <el-table-column :label="$t('adminDataManage.category')" width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.data_source || '-' }}</template>
      </el-table-column>
      <el-table-column :label="$t('adminDataManage.description')" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.data_introduction || '-' }}</template>
      </el-table-column>
      <el-table-column label="GeoServer" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.data_url ? 'success' : 'info'" size="small">
            {{ row.data_url ? 'OK' : '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="activeTab === 'raster'" :label="$t('adminDataManage.bands')" width="80" align="center">
        <template #default="{ row }">{{ row.band_count ?? '-' }}</template>
      </el-table-column>
      <el-table-column v-if="activeTab === 'raster'" label="Pixel" width="80" align="center">
        <template #default="{ row }">{{ row.pixel_type || '-' }}</template>
      </el-table-column>
      <el-table-column :label="$t('adminDataManage.actions')" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openEdit(row)">{{ $t('adminDataManage.edit') }}</el-button>
          <el-button size="small" type="warning" link @click="handlePublish(row)" :loading="row._publishing">
            {{ $t('adminDataManage.publish') }}
          </el-button>
          <el-popconfirm :title="$t('adminDataManage.confirmDelete')" @confirm="handleDelete(row)">
            <template #reference>
              <el-button size="small" type="danger" link>{{ $t('adminDataManage.delete') }}</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap" v-if="total > pageSize">
      <el-pagination background layout="total, prev, pager, next" :total="total"
        v-model:current-page="currentPage" :page-size="pageSize" @current-change="fetchData" />
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editVisible" :title="$t('adminDataManage.editTitle')" width="500px" destroy-on-close>
      <el-form :model="editForm" label-position="top">
        <el-form-item :label="$t('adminDataManage.dataName')">
          <el-input v-model="editForm.alias" />
        </el-form-item>
        <el-form-item :label="$t('adminDataManage.category')">
          <el-input v-model="editForm.data_source" />
        </el-form-item>
        <el-form-item :label="$t('adminDataManage.description')">
          <el-input v-model="editForm.introduction" type="textarea" :rows="5" show-word-limit maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">{{ $t('adminDataManage.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">{{ $t('adminDataManage.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDataList, updateData, deleteData, publishToGeoServer } from '@/api/upload'

const { t } = useI18n()

const activeTab = ref('vector')
const dataList = ref([])
const loading = ref(false)
const keyword = ref('')
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)

// Edit dialog
const editVisible = ref(false)
const saving = ref(false)
const editForm = reactive({ id: null, alias: '', introduction: '', data_source: '' })

const fetchData = async () => {
  loading.value = true
  try {
    const { data } = await getDataList(activeTab.value, {
      page: currentPage.value,
      pageSize,
      keyword: keyword.value || undefined,
    })
    dataList.value = (data?.list || []).map(item => ({ ...item, _publishing: false }))
    total.value = data?.total || 0
  } catch {
    dataList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handleTabChange = () => {
  currentPage.value = 1
  keyword.value = ''
  fetchData()
}

const openEdit = (row) => {
  editForm.id = row.data_id
  editForm.alias = row.data_alias || ''
  editForm.introduction = row.data_introduction || ''
  editForm.data_source = row.data_source || ''
  editVisible.value = true
}

const handleSave = async () => {
  saving.value = true
  try {
    const { status, msg } = await updateData(activeTab.value, editForm.id, {
      alias: editForm.alias,
      introduction: editForm.introduction,
      data_source: editForm.data_source,
    })
    if (status) {
      ElMessage.success(msg || t('adminDataManage.saveSuccess'))
      editVisible.value = false
      fetchData()
    } else {
      ElMessage.error(msg || t('adminDataManage.saveFailed'))
    }
  } catch {
    ElMessage.error(t('adminDataManage.saveFailed'))
  } finally {
    saving.value = false
  }
}

const handlePublish = async (row) => {
  row._publishing = true
  try {
    const { status, msg } = await publishToGeoServer({ data_type: activeTab.value, data_id: row.data_id })
    if (status) {
      ElMessage.success(msg || t('adminDataManage.publishSuccess'))
      fetchData()
    } else {
      ElMessage.error(msg || t('adminDataManage.publishFailed'))
    }
  } catch {
    ElMessage.error(t('adminDataManage.publishFailed'))
  } finally {
    row._publishing = false
  }
}

const handleDelete = async (row) => {
  try {
    const { status, msg } = await deleteData(activeTab.value, row.data_id)
    if (status) {
      ElMessage.success(msg || t('adminDataManage.deleteSuccess'))
      fetchData()
    } else {
      ElMessage.error(msg || t('adminDataManage.deleteFailed'))
    }
  } catch {
    ElMessage.error(t('adminDataManage.deleteFailed'))
  }
}

onMounted(fetchData)
</script>

<style scoped>
.data-manage-container { padding: 24px 40px; background-color: #f7f8fa; min-height: calc(100vh - 50px); }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 24px; font-weight: 600; color: #1d2129; margin: 0 0 8px 0; }
.page-description { font-size: 14px; color: #86909c; margin: 0; }
.data-tabs { margin-bottom: 16px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.pagination-wrap { margin-top: 20px; display: flex; justify-content: flex-end; }
</style>
