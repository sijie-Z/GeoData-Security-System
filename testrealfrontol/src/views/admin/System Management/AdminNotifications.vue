<template>
  <div class="admin-notify-page">
    <div class="page-header">
      <h1 class="page-title">个人消息发送</h1>
      <p class="page-desc">向指定员工或全体员工发送个人消息（进入员工“我的通知”）</p>
    </div>

    <el-card class="notify-card" shadow="hover">
      <el-form :model="form" label-width="96px" class="notify-form">
        <el-form-item label="通知标题" required>
          <el-input v-model="form.title" maxlength="80" show-word-limit placeholder="请输入通知标题" />
        </el-form-item>

        <el-form-item label="通知内容" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="5"
            maxlength="2000"
            show-word-limit
            placeholder="请输入通知内容"
          />
        </el-form-item>

        <el-form-item label="发送对象">
          <el-radio-group v-model="sendMode">
            <el-radio value="all">全体员工</el-radio>
            <el-radio value="specified">指定员工</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="sendMode === 'specified'" label="员工编号">
          <el-select
            v-model="form.user_numbers"
            multiple
            filterable
            clearable
            default-first-option
            placeholder="请选择或输入员工编号"
            style="width: 100%"
          >
            <el-option
              v-for="u in employeeOptions"
              :key="u.value"
              :label="u.label"
              :value="u.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="sending" @click="sendNotification">发送通知</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import Axios from '@/utils/Axios'

const sending = ref(false)
const sendMode = ref('all')
const employeeOptions = ref([])

const form = reactive({
  title: '',
  content: '',
  user_numbers: []
})

const loadEmployees = async () => {
  try {
    const { data } = await Axios.get(`/api/admin/get_employee_info`)
    const list = data?.data?.list || []
    employeeOptions.value = list.map((i) => ({
      label: `${i.employee_number}${i.name ? ` - ${i.name}` : ''}`,
      value: i.employee_number
    }))
  } catch (_e) {
    employeeOptions.value = []
  }
}

const sendNotification = async () => {
  const title = (form.title || '').trim()
  const content = (form.content || '').trim()
  if (!title) {
    ElMessage.warning('请输入通知标题')
    return
  }
  if (!content) {
    ElMessage.warning('请输入通知内容')
    return
  }
  if (sendMode.value === 'specified' && (!form.user_numbers || form.user_numbers.length === 0)) {
    ElMessage.warning('请选择至少一个员工')
    return
  }

  sending.value = true
  try {
    const payload = {
      title,
      content,
      user_numbers: sendMode.value === 'all' ? [] : form.user_numbers
    }
    const { data } = await Axios.post(`/api/admin/notifications/send`, payload)
    if (data?.status) {
      ElMessage.success(data?.msg || '发送成功')
      resetForm()
    } else {
      ElMessage.error(data?.msg || '发送失败')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || '发送失败')
  } finally {
    sending.value = false
  }
}

const resetForm = () => {
  form.title = ''
  form.content = ''
  form.user_numbers = []
  sendMode.value = 'all'
}

onMounted(loadEmployees)
</script>

<style scoped>
.admin-notify-page { padding: 24px; max-width: 980px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { margin: 0 0 8px; font-size: 22px; color: #1f2937; }
.page-desc { margin: 0; color: #6b7280; }
.notify-card { border-radius: 12px; }
.notify-form { max-width: 860px; }
</style>
