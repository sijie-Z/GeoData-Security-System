<template>
  <el-popover
    placement="bottom-end"
    :width="360"
    trigger="click"
    v-model:visible="showPopover"
  >
    <template #reference>
      <div class="notification-bell" @click="markAllAsRead">
        <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
          <el-icon :size="20"><Bell /></el-icon>
        </el-badge>
      </div>
    </template>

    <div class="notification-panel">
      <div class="panel-header">
        <span class="panel-title">{{ $t('notification.center') }}</span>
        <el-button type="primary" link size="small" @click="goToChat" v-if="unreadMessages > 0">
          {{ $t('notification.newMessages', { count: unreadMessages }) }}
        </el-button>
      </div>

      <el-tabs v-model="activeTab" class="notification-tabs">
        <el-tab-pane :label="$t('notification.messages')" name="messages">
          <div class="notification-list" v-loading="loading">
            <div v-if="messageNotifications.length === 0" class="empty-state">
              {{ $t('notification.noMessages') }}
            </div>
            <div
              v-for="item in messageNotifications"
              :key="item.peer_number + item.peer_role"
              class="notification-item"
              :class="{ unread: item.unread_count > 0 }"
              @click="goToMessage(item)"
            >
              <div class="avatar">{{ (item.peer_name || item.peer_number || '?').charAt(0) }}</div>
              <div class="content">
                <div class="item-header">
                  <span class="sender">{{ item.peer_name || item.peer_number }}</span>
                  <span class="time">{{ formatTime(item.last_time) }}</span>
                </div>
                <div class="preview">{{ item.last_message || $t('notification.clickToView') }}</div>
              </div>
              <el-badge v-if="item.unread_count > 0" :value="item.unread_count" class="item-badge" />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="$t('notification.systemNotifications')" name="system">
          <div class="notification-list" v-loading="loading">
            <div v-if="systemNotifications.length === 0" class="empty-state">
              {{ $t('notification.noSystemNotifications') }}
            </div>
            <div
              v-for="item in systemNotifications"
              :key="item.id"
              class="notification-item system-item"
              :class="{ unread: !item.read }"
              @click="handleSystemNotification(item)"
            >
              <div class="icon-wrapper" :class="item.type || 'info'">
                <el-icon v-if="item.type === 'approval'"><DocumentChecked /></el-icon>
                <el-icon v-else-if="item.type === 'recall'"><Warning /></el-icon>
                <el-icon v-else><Bell /></el-icon>
              </div>
              <div class="content">
                <div class="item-header">
                  <span class="sender">{{ item.title }}</span>
                  <span class="time">{{ formatTime(item.created_at) }}</span>
                </div>
                <div class="preview">{{ item.content }}</div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-popover>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Bell, DocumentChecked, Warning } from '@element-plus/icons-vue'
import Axios from '@/utils/Axios'
import { useUserStore } from '@/stores/userStore'

const { t } = useI18n()
const router = useRouter()
const userStore = useUserStore()

const showPopover = ref(false)
const activeTab = ref('messages')
const loading = ref(false)
const messageNotifications = ref([])
const systemNotifications = ref([])

const unreadMessages = computed(() => {
  return messageNotifications.value.reduce((sum, item) => sum + (item.unread_count || 0), 0)
})

const unreadCount = computed(() => {
  const systemUnread = systemNotifications.value.filter(n => !n.read).length
  return unreadMessages.value + systemUnread
})

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return t('notification.justNow')
  if (diff < 3600000) return t('notification.minutesAgo', { n: Math.floor(diff / 60000) })
  if (diff < 86400000) return t('notification.hoursAgo', { n: Math.floor(diff / 3600000) })
  return timeStr.slice(5, 16)
}

const loadConversations = async () => {
  try {
    const { data } = await Axios.get('/api/chat/conversations')
    if (data?.status) {
      messageNotifications.value = (data.data || []).filter(c => c.unread_count > 0).slice(0, 10)
    }
  } catch (e) {
    console.error('Failed to load conversations:', e)
  }
}

const loadSystemNotifications = async () => {
  try {
    const role = userStore.currentUser?.role
    const endpoint = role === 'admin' ? '/api/employee/notifications' : '/api/employee/notifications'
    const { data } = await Axios.get(endpoint, {
      params: { unread_only: true, pageSize: 10 }
    })
    if (data?.status) {
      systemNotifications.value = data.data?.list || []
    }
  } catch (e) {
    systemNotifications.value = []
  }
}

const markAllAsRead = () => {
  systemNotifications.value.forEach(n => n.read = true)
}

const goToChat = () => {
  showPopover.value = false
  const role = userStore.currentUser?.role
  if (role === 'admin') {
    router.push('/admin/system/chat')
  } else {
    router.push('/employee/chat')
  }
}

const goToMessage = (item) => {
  showPopover.value = false
  const role = userStore.currentUser?.role
  if (role === 'admin') {
    router.push('/admin/system/chat')
  } else {
    router.push('/employee/chat')
  }
}

const handleSystemNotification = (item) => {
  showPopover.value = false
  if (item.type === 'approval') {
    router.push('/admin/approve_application/not_approved')
  } else if (item.type === 'recall') {
    router.push('/admin/recall')
  } else if (item.related_url) {
    router.push(item.related_url)
  }
}

let pollTimer = null

onMounted(() => {
  loadConversations()
  loadSystemNotifications()
  pollTimer = setInterval(() => {
    if (document.visibilityState === 'visible') {
      loadConversations()
      loadSystemNotifications()
    }
  }, 60000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.notification-bell {
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-bell:hover {
  background: rgba(255, 255, 255, 0.1);
}

.notification-panel {
  max-height: 400px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}

.panel-title {
  font-weight: 600;
  font-size: 16px;
}

.notification-tabs {
  margin-top: 12px;
}

.notification-list {
  max-height: 300px;
  overflow-y: auto;
}

.empty-state {
  text-align: center;
  color: #909399;
  padding: 40px 20px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: #f5f7fa;
}

.notification-item.unread {
  background: #ecf5ff;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #67c23a);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.icon-wrapper.info { background: #409eff; }
.icon-wrapper.approval { background: #67c23a; }
.icon-wrapper.recall { background: #e6a23c; }

.content {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.sender {
  font-weight: 500;
  color: #303133;
  font-size: 14px;
}

.time {
  font-size: 12px;
  color: #909399;
}

.preview {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-badge {
  flex-shrink: 0;
}
</style>
