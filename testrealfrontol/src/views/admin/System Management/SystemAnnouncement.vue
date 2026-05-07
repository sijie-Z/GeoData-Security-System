<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled, CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'
import Axios from '@/utils/Axios'

const loading = ref(false)
const list = ref([])
const pages = reactive({ page: 1, pageSize: 10, total: 0, pages: 0 })

const formVisible = ref(false)
const formTitle = ref('发布系统公告')
const form = reactive({
  id: null,
  title: '',
  content: '',
  tag: '重要',
  tag_color: '#F59E0B',
  icon: 'InfoFilled'
})

// 说明：个人消息发送已独立到“个人消息发送”页面，公告页仅处理公共公告

const fetchAnnouncements = async () => {
  loading.value = true
  try {
    const { data } = await Axios.get('/api/announcements', {
      params: { page: pages.page, pageSize: pages.pageSize }
    })
    if (data?.status) {
      list.value = data.data.list || []
      Object.assign(pages, data.data.pages || pages)
    } else {
      list.value = []
      pages.total = 0
    }
  } catch (e) {
    ElMessage.error('获取公告失败')
  } finally {
    loading.value = false
  }
}


// 小白说明：打开发布或编辑弹窗
const openForm = (row = null) => {
  if (row) {
    formTitle.value = '编辑系统公告'
    Object.assign(form, {
      id: row.id,
      title: row.title,
      content: row.content,
      tag: row.tag || '重要',
      tag_color: row.tag_color || '#F59E0B',
      icon: row.icon || 'InfoFilled'
    })
  } else {
    formTitle.value = '发布系统公告'
    Object.assign(form, { id: null, title: '', content: '', tag: '重要', tag_color: '#F59E0B', icon: 'InfoFilled' })
  }
  formVisible.value = true
}

// 小白说明：保存公告（发布或编辑）
const submitForm = async () => {
  try {
    if (!form.title || !form.content) {
      ElMessage.warning('标题和内容不能为空')
      return
    }
    if (form.id) {
      await Axios.put('/api/admin/announcements', form)
      ElMessage.success('更新成功')
    } else {
      await Axios.post('/api/admin/announcements', form)
      ElMessage.success('发布成功')
    }
    formVisible.value = false
    fetchAnnouncements()
  } catch (e) {
    ElMessage.error('保存失败，请检查权限或网络')
  }
}

// 小白说明：删除公告（逻辑删除）
const removeAnnouncement = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '提示', { type: 'warning' })
    await Axios.delete('/api/admin/announcements', { params: { id: row.id } })
    ElMessage.success('已移除')
    fetchAnnouncements()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const nextPage = () => { if (pages.page < pages.pages) { pages.page += 1; fetchAnnouncements() } }
const prevPage = () => { if (pages.page > 1) { pages.page -= 1; fetchAnnouncements() } }

onMounted(fetchAnnouncements)
</script>

<template>
  <div class="announcement-admin">
    <div class="header">
      <h2>系统公告（公共广播）</h2>
      <div class="header-actions">
        <el-button type="primary" @click="openForm()">发布公告</el-button>
      </div>
    </div>

    <el-card class="mb-3 notify-card">
      <template #header><span class="card-label">说明：公告与个人消息的区别</span></template>
      <p class="card-desc">系统公告用于面向全体用户的公共信息发布；若要向指定员工或全体员工发送个人消息，请前往「系统管理 → 个人消息发送」。</p>
    </el-card>

    <el-card class="mb-3">
      <template #header><span class="card-label">系统公告列表</span></template>
      <el-table :data="list" v-loading="loading" border>
        <el-table-column label="图标" width="80">
          <template #default="{ row }">
            <el-icon :style="{ color: row.tag_color }">
              <component :is="row.icon === 'CircleCheckFilled' ? CircleCheckFilled : row.icon === 'WarningFilled' ? WarningFilled : InfoFilled" />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column label="标签" width="140">
          <template #default="{ row }">
            <el-tag :style="{ backgroundColor: row.tag_color, color: '#fff', borderColor: row.tag_color }">{{ row.tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="内容" min-width="320" />
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button link type="primary" @click="openForm(row)">编辑</el-button>
            <el-button link type="danger" @click="removeAnnouncement(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-button :disabled="pages.page<=1" @click="prevPage">上一页</el-button>
        <span>第 {{ pages.page }} / {{ pages.pages }} 页，共 {{ pages.total }} 条</span>
        <el-button :disabled="pages.page>=pages.pages" @click="nextPage">下一页</el-button>
      </div>
    </el-card>

    <el-dialog v-model="formVisible" :title="formTitle" width="620px" draggable custom-class="rounded-dialog">
      <el-form label-width="88px">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="请输入公告标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="5" placeholder="请输入公告内容" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tag" style="width: 160px">
            <el-option label="重要" value="重要" />
            <el-option label="新数据" value="新数据" />
            <el-option label="优化" value="优化" />
            <el-option label="自定义" value="自定义" />
          </el-select>
          <el-color-picker v-model="form.tag_color" style="margin-left: 12px" />
        </el-form-item>
        <el-form-item label="图标">
          <el-select v-model="form.icon" style="width: 200px">
            <el-option label="信息" value="InfoFilled" />
            <el-option label="通过" value="CircleCheckFilled" />
            <el-option label="警告" value="WarningFilled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible=false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
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
