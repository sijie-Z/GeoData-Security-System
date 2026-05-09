<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled, CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'
import {
  getAnnouncements,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement
} from '@/api/admin'

const { t } = useI18n()

const loading = ref(false)
const list = ref([])
const pages = reactive({ page: 1, pageSize: 10, total: 0, pages: 0 })

const formVisible = ref(false)
const formTitle = ref(t('adminAnnounce.publishTitle'))
const form = reactive({
  id: null,
  title: '',
  content: '',
  tag: '重要',
  tag_color: '#F59E0B',
  icon: 'InfoFilled'
})

// 说明：个人消息发送已独立到"个人消息发送"页面，公告页仅处理公共公告

const fetchAnnouncements = async () => {
  loading.value = true
  try {
    const { data } = await getAnnouncements({ page: pages.page, pageSize: pages.pageSize })
    if (data?.status) {
      list.value = data.data.list || []
      Object.assign(pages, data.data.pages || pages)
    } else {
      list.value = []
      pages.total = 0
    }
  } catch (e) {
    ElMessage.error(t('adminAnnounce.fetchFailed'))
  } finally {
    loading.value = false
  }
}


// 小白说明：打开发布或编辑弹窗
const openForm = (row = null) => {
  if (row) {
    formTitle.value = t('adminAnnounce.editTitle')
    Object.assign(form, {
      id: row.id,
      title: row.title,
      content: row.content,
      tag: row.tag || '重要',
      tag_color: row.tag_color || '#F59E0B',
      icon: row.icon || 'InfoFilled'
    })
  } else {
    formTitle.value = t('adminAnnounce.publishTitle')
    Object.assign(form, { id: null, title: '', content: '', tag: '重要', tag_color: '#F59E0B', icon: 'InfoFilled' })
  }
  formVisible.value = true
}

// 小白说明：保存公告（发布或编辑）
const submitForm = async () => {
  try {
    if (!form.title || !form.content) {
      ElMessage.warning(t('adminAnnounce.titleContentRequired'))
      return
    }
    if (form.id) {
      await updateAnnouncement(form)
      ElMessage.success(t('adminAnnounce.updateSuccess'))
    } else {
      await createAnnouncement(form)
      ElMessage.success(t('adminAnnounce.publishSuccess'))
    }
    formVisible.value = false
    fetchAnnouncements()
  } catch (e) {
    ElMessage.error(t('adminAnnounce.saveFailed'))
  }
}

// 小白说明：删除公告（逻辑删除）
const removeAnnouncement = async (row) => {
  try {
    await ElMessageBox.confirm(t('adminAnnounce.confirmDelete', { title: row.title }), t('adminAnnounce.tip'), { type: 'warning' })
    await deleteAnnouncement(row.id)
    ElMessage.success(t('adminAnnounce.removed'))
    fetchAnnouncements()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('adminAnnounce.deleteFailed'))
  }
}

const nextPage = () => { if (pages.page < pages.pages) { pages.page += 1; fetchAnnouncements() } }
const prevPage = () => { if (pages.page > 1) { pages.page -= 1; fetchAnnouncements() } }

onMounted(fetchAnnouncements)
</script>

<template>
  <div class="announcement-admin">
    <div class="header">
      <h2>{{ $t('adminAnnounce.title') }}</h2>
      <div class="header-actions">
        <el-button type="primary" @click="openForm()">{{ $t('adminAnnounce.publish') }}</el-button>
      </div>
    </div>

    <el-card class="mb-3 notify-card">
      <template #header><span class="card-label">{{ $t('adminAnnounce.explanation') }}</span></template>
      <p class="card-desc">{{ $t('adminAnnounce.explanationDesc') }}</p>
    </el-card>

    <el-card class="mb-3">
      <template #header><span class="card-label">{{ $t('adminAnnounce.announcementList') }}</span></template>
      <el-table :data="list" v-loading="loading" border>
        <el-table-column :label="$t('adminAnnounce.icon')" width="80">
          <template #default="{ row }">
            <el-icon :style="{ color: row.tag_color }">
              <component :is="row.icon === 'CircleCheckFilled' ? CircleCheckFilled : row.icon === 'WarningFilled' ? WarningFilled : InfoFilled" />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column prop="title" :label="$t('adminAnnounce.titleLabel')" min-width="200" />
        <el-table-column :label="$t('adminAnnounce.tag')" width="140">
          <template #default="{ row }">
            <el-tag :style="{ backgroundColor: row.tag_color, color: '#fff', borderColor: row.tag_color }">{{ row.tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" :label="$t('adminAnnounce.content')" min-width="320" />
        <el-table-column prop="created_at" :label="$t('adminAnnounce.time')" width="180" />
        <el-table-column :label="$t('adminAnnounce.action')" width="180">
          <template #default="{ row }">
            <el-button link type="primary" @click="openForm(row)">{{ $t('adminAnnounce.edit') }}</el-button>
            <el-button link type="danger" @click="removeAnnouncement(row)">{{ $t('adminAnnounce.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-button :disabled="pages.page<=1" @click="prevPage">{{ $t('adminAnnounce.prevPage') }}</el-button>
        <span>{{ $t('adminAnnounce.pageInfo', { page: pages.page, pages: pages.pages, total: pages.total }) }}</span>
        <el-button :disabled="pages.page>=pages.pages" @click="nextPage">{{ $t('adminAnnounce.nextPage') }}</el-button>
      </div>
    </el-card>

    <el-dialog v-model="formVisible" :title="formTitle" width="620px" draggable custom-class="rounded-dialog">
      <el-form label-width="88px">
        <el-form-item :label="$t('adminAnnounce.titleLabel')">
          <el-input v-model="form.title" :placeholder="$t('adminAnnounce.titlePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('adminAnnounce.content')">
          <el-input v-model="form.content" type="textarea" :rows="5" :placeholder="$t('adminAnnounce.contentPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('adminAnnounce.tag')">
          <el-select v-model="form.tag" style="width: 160px">
            <el-option :label="$t('adminAnnounce.tagImportant')" value="重要" />
            <el-option :label="$t('adminAnnounce.tagNewData')" value="新数据" />
            <el-option :label="$t('adminAnnounce.tagOptimize')" value="优化" />
            <el-option :label="$t('adminAnnounce.tagCustom')" value="自定义" />
          </el-select>
          <el-color-picker v-model="form.tag_color" style="margin-left: 12px" />
        </el-form-item>
        <el-form-item :label="$t('adminAnnounce.icon')">
          <el-select v-model="form.icon" style="width: 200px">
            <el-option :label="$t('adminAnnounce.iconInfo')" value="InfoFilled" />
            <el-option :label="$t('adminAnnounce.iconPass')" value="CircleCheckFilled" />
            <el-option :label="$t('adminAnnounce.iconWarning')" value="WarningFilled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible=false">{{ $t('adminAnnounce.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm">{{ $t('adminAnnounce.save') }}</el-button>
      </template>
    </el-dialog>


  </div>
</template>

<style scoped>
.announcement-admin { padding: 16px }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px }
.header-actions { display: flex; gap: 8px }
.notify-card { margin-bottom: 16px }
.card-label { font-weight: 600 }
.card-desc { color: #6b7280; font-size: 13px; margin: 0 0 12px 0 }
.form-tip { font-size: 12px; color: #9ca3af; margin-top: 4px }
.mb-3 { margin-bottom: 12px }
.pagination { display: flex; gap: 12px; align-items: center; padding: 12px }
.rounded-dialog { border-radius: 14px; overflow: hidden; }
</style>
