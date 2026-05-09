<template>
  <div class="admin-notify-page">
    <div class="page-header">
      <h1 class="page-title">{{ $t('adminNotify.title') }}</h1>
      <p class="page-desc">{{ $t('adminNotify.description') }}</p>
    </div>

    <el-card class="notify-card" shadow="hover">
      <el-form :model="form" label-width="96px" class="notify-form">
        <el-form-item :label="$t('adminNotify.titleLabel')" required>
          <el-input v-model="form.title" maxlength="80" show-word-limit :placeholder="$t('adminNotify.titlePlaceholder')" />
        </el-form-item>

        <el-form-item :label="$t('adminNotify.contentLabel')" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="5"
            maxlength="2000"
            show-word-limit
            :placeholder="$t('adminNotify.contentPlaceholder')"
          />
        </el-form-item>

        <el-form-item :label="$t('adminNotify.sendTarget')">
          <el-radio-group v-model="sendMode">
            <el-radio value="all">{{ $t('adminNotify.allEmployees') }}</el-radio>
            <el-radio value="specified">{{ $t('adminNotify.specifiedEmployees') }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="sendMode === 'specified'" :label="$t('adminNotify.employeeNumber')">
          <el-select
            v-model="form.user_numbers"
            multiple
            filterable
            clearable
            default-first-option
            :placeholder="$t('adminNotify.selectEmployee')"
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
          <el-button type="primary" :loading="sending" @click="sendNotification">{{ $t('adminNotify.sendNotification') }}</el-button>
          <el-button @click="resetForm">{{ $t('adminNotify.reset') }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getEmployeeInfo, sendNotification as sendNotificationApi } from '@/api/admin'

const { t } = useI18n()

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
    const { data } = await getEmployeeInfo()
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
    ElMessage.warning(t('adminNotify.enterTitle'))
    return
  }
  if (!content) {
    ElMessage.warning(t('adminNotify.enterContent'))
    return
  }
  if (sendMode.value === 'specified' && (!form.user_numbers || form.user_numbers.length === 0)) {
    ElMessage.warning(t('adminNotify.selectAtLeastOne'))
    return
  }

  sending.value = true
  try {
    const payload = {
      title,
      content,
      user_numbers: sendMode.value === 'all' ? [] : form.user_numbers
    }
    const { data } = await sendNotificationApi(payload)
    if (data?.status) {
      ElMessage.success(data?.msg || t('adminNotify.sendSuccess'))
      resetForm()
    } else {
      ElMessage.error(data?.msg || t('adminNotify.sendFailed'))
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || t('adminNotify.sendFailed'))
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
