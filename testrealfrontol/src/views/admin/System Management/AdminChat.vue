<template>
  <div class="chat-page">
    <el-card class="chat-card" shadow="hover">
      <template #header>
        <div class="chat-header">
          <h2>在线沟通中心</h2>
          <el-button type="primary" @click="showUserList = true" :icon="Plus">选择联系人</el-button>
        </div>
      </template>

      <div class="chat-layout">
        <!-- 会话列表 -->
        <aside class="conversation-list">
          <div class="list-header">最近会话</div>
          <div class="conversations" v-loading="loadingConversations">
            <div
              v-for="item in conversations"
              :key="`${item.peer_role}-${item.peer_number}`"
              class="conversation-item"
              :class="{ active: activePeer && activePeer.peer_number === item.peer_number && activePeer.peer_role === item.peer_role }"
              @click="selectConversation(item)"
            >
              <div class="avatar">{{ (item.peer_name || item.peer_number || '?').charAt(0) }}</div>
              <div class="info">
                <div class="name">{{ item.peer_name || item.peer_number }}</div>
                <div class="preview">{{ item.last_message || '点击开始聊天' }}</div>
              </div>
              <el-badge v-if="item.unread_count > 0" :value="item.unread_count" />
            </div>
            <div v-if="conversations.length === 0 && !loadingConversations" class="no-session">
              <p>暂无会话记录</p>
              <el-button type="primary" size="small" @click="showUserList = true">开始聊天</el-button>
            </div>
          </div>
        </aside>

        <!-- 聊天区域 -->
        <section class="chat-area">
          <div v-if="!activePeer" class="empty-chat">
            <el-empty description="请选择联系人开始聊天">
              <el-button type="primary" @click="showUserList = true">选择联系人</el-button>
            </el-empty>
          </div>

          <template v-else>
            <!-- 聊天头部 -->
            <div class="chat-top-bar">
              <div class="peer-info">
                <span class="peer-name">{{ activePeer.peer_name || activePeer.peer_number }}</span>
                <el-tag size="small" :type="activePeer.peer_role === 'admin' ? 'warning' : 'success'">
                  {{ activePeer.peer_role === 'admin' ? '管理员' : '员工' }}
                </el-tag>
              </div>
              <el-button size="small" @click="loadMessages" :loading="loadingMessages">刷新</el-button>
            </div>

            <!-- 消息列表 -->
            <div class="messages" ref="messageBoxRef" v-loading="loadingMessages">
              <div v-for="msg in messages" :key="msg.id" class="msg-item" :class="{ me: msg.is_me }">
                <div class="bubble">{{ msg.content }}</div>
                <div class="time">{{ msg.created_at }}</div>
              </div>
              <div v-if="messages.length === 0 && !loadingMessages" class="no-msg">
                <p>暂无消息</p>
                <p>发送第一条消息开始聊天</p>
              </div>
            </div>

            <!-- 输入区域 -->
            <div class="input-area">
              <el-input
                v-model="messageText"
                type="textarea"
                :rows="3"
                placeholder="输入消息内容，按 Ctrl+Enter 发送"
                @keydown.ctrl.enter="sendMessage"
              />
              <div class="input-actions">
                <el-button type="primary" @click="sendMessage" :loading="sending" :disabled="!messageText.trim()">
                  发送
                </el-button>
              </div>
            </div>
          </template>
        </section>
      </div>
    </el-card>

    <!-- 用户选择对话框 -->
    <el-dialog v-model="showUserList" title="选择联系人" width="600px" destroy-on-close>
      <el-input v-model="userSearchKeyword" placeholder="搜索用户名或编号" clearable style="margin-bottom: 16px" />
      <el-tabs v-model="userListTab">
        <el-tab-pane label="员工列表" name="employees">
          <el-table :data="filteredEmployees" max-height="400" v-loading="loadingUsers">
            <el-table-column prop="employee_number" label="编号" width="120" />
            <el-table-column prop="name" label="姓名" />
            <el-table-column label="操作" width="100">
              <template #default="scope">
                <el-button type="primary" size="small" @click="startChat(scope.row, 'employee')">聊天</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="管理员列表" name="admins">
          <el-table :data="filteredAdmins" max-height="400" v-loading="loadingUsers">
            <el-table-column prop="adm_number" label="编号" width="120" />
            <el-table-column prop="name" label="姓名" />
            <el-table-column label="操作" width="100">
              <template #default="scope">
                <el-button type="primary" size="small" @click="startChat(scope.row, 'admin')">聊天</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import Axios from '@/utils/Axios'
import { useUserStore } from '@/stores/userStore'

const userStore = useUserStore()

const conversations = ref([])
const messages = ref([])
const activePeer = ref(null)
const messageText = ref('')
const sending = ref(false)
const loadingConversations = ref(false)
const loadingMessages = ref(false)
const loadingUsers = ref(false)
const showUserList = ref(false)
const userListTab = ref('employees')
const userSearchKeyword = ref('')
const employees = ref([])
const admins = ref([])
const messageBoxRef = ref(null)

let pollTimer = null

const filteredEmployees = computed(() => {
  const kw = (userSearchKeyword.value || '').toLowerCase()
  if (!kw) return employees.value
  return employees.value.filter(e =>
    ((e.name || '')).toLowerCase().includes(kw) ||
    ((e.employee_number || '')).toLowerCase().includes(kw)
  )
})

const filteredAdmins = computed(() => {
  const kw = (userSearchKeyword.value || '').toLowerCase()
  if (!kw) return admins.value
  return admins.value.filter(a =>
    ((a.name || '')).toLowerCase().includes(kw) ||
    ((a.adm_number || '')).toLowerCase().includes(kw)
  )
})

const scrollToBottom = async () => {
  await nextTick()
  if (messageBoxRef.value) {
    messageBoxRef.value.scrollTop = messageBoxRef.value.scrollHeight
  }
}

const loadConversations = async () => {
  loadingConversations.value = true
  try {
    const { data } = await Axios.get('/api/chat/conversations')
    if (data?.status) {
      conversations.value = data.data || []
    }
  } catch (e) {
    console.error('加载会话失败:', e)
  } finally {
    loadingConversations.value = false
  }
}

const loadMessages = async () => {
  if (!activePeer.value) return
  loadingMessages.value = true
  try {
    const { data } = await Axios.get('/api/chat/messages', {
      params: {
        peer_number: activePeer.value.peer_number,
        peer_role: activePeer.value.peer_role
      }
    })
    if (data?.status) {
      messages.value = data.data || []
      await scrollToBottom()
      // 标记已读
      await Axios.post('/api/chat/mark_read', {
        peer_number: activePeer.value.peer_number,
        peer_role: activePeer.value.peer_role
      })
      // 更新会话列表中的未读数
      await loadConversations()
    }
  } catch (e) {
    console.error('加载消息失败:', e)
  } finally {
    loadingMessages.value = false
  }
}

const selectConversation = async (item) => {
  activePeer.value = {
    peer_number: item.peer_number,
    peer_role: item.peer_role,
    peer_name: item.peer_name
  }
  await loadMessages()
}

const sendMessage = async () => {
  if (!activePeer.value) {
    ElMessage.warning('请先选择联系人')
    return
  }
  const content = (messageText.value || '').trim()
  if (!content) {
    ElMessage.warning('消息不能为空')
    return
  }
  sending.value = true
  try {
    const { data } = await Axios.post('/api/chat/send', {
      receiver_number: activePeer.value.peer_number,
      receiver_role: activePeer.value.peer_role,
      content
    })
    if (data?.status) {
      messageText.value = ''
      await loadMessages()
    } else {
      ElMessage.error(data?.msg || '发送失败')
    }
  } catch (e) {
    ElMessage.error('发送失败')
  } finally {
    sending.value = false
  }
}

const loadAllUsers = async () => {
  loadingUsers.value = true
  try {
    const { data } = await Axios.get('/api/admin/users')
    if (data?.status) {
      employees.value = data.data?.employees || []
      admins.value = data.data?.admins || []
    }
  } catch (e) {
    console.error('加载用户失败:', e)
    // 备用方案
    try {
      const empRes = await Axios.get('/api/adm/get_emp_info_list', { params: { pageSize: 1000 } })
      employees.value = empRes.data?.data?.list || empRes.data?.data || []
    } catch (e2) {
      console.error('备用加载员工失败:', e2)
    }
  } finally {
    loadingUsers.value = false
  }
}

const startChat = (row, role) => {
  const number = role === 'employee' ? row.employee_number : row.adm_number
  // 检查是否选择自己
  if (number === userStore.userNumber) {
    ElMessage.warning('不能和自己聊天')
    return
  }
  activePeer.value = {
    peer_number: number,
    peer_role: role,
    peer_name: row.name
  }
  showUserList.value = false
  loadMessages()
}

onMounted(async () => {
  await Promise.all([loadConversations(), loadAllUsers()])
  // 使用visibilitychange优化性能
  document.addEventListener('visibilitychange', handleVisibilityChange)
  startPolling()
})

const startPolling = () => {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    // 只在页面可见时刷新
    if (document.visibilityState === 'visible') {
      await loadConversations()
      if (activePeer.value) await loadMessages()
    }
  }, 30000) // 改为30秒，减少刷新频率
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    // 页面重新可见时立即刷新一次
    loadConversations()
    if (activePeer.value) loadMessages()
  }
}

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.chat-page { padding: 20px; background: #f5f7fa; min-height: calc(100vh - 60px); }
.chat-card { border-radius: 12px; }
.chat-header { display: flex; justify-content: space-between; align-items: center; }
.chat-header h2 { margin: 0; font-size: 18px; color: #303133; }

.chat-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
  min-height: 550px;
}

/* 会话列表 */
.conversation-list {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
}
.list-header {
  padding: 14px 16px;
  font-weight: 600;
  color: #303133;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  border-radius: 10px 10px 0 0;
}
.conversations { height: 500px; overflow-y: auto; padding: 8px; }
.conversation-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.2s;
}
.conversation-item:hover { background: #f5f7fa; }
.conversation-item.active { background: #ecf5ff; border-left: 3px solid #409eff; }
.avatar {
  width: 40px; height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff, #67c23a);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 600;
}
.info { flex: 1; min-width: 0; }
.info .name { font-weight: 600; color: #303133; font-size: 14px; }
.info .preview { color: #909399; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.no-session { text-align: center; padding: 40px 20px; color: #909399; }
.no-session p { margin-bottom: 12px; }

/* 聊天区域 */
.chat-area {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
  display: flex;
  flex-direction: column;
}
.empty-chat { flex: 1; display: flex; align-items: center; justify-content: center; }
.chat-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  border-radius: 10px 10px 0 0;
}
.peer-info { display: flex; align-items: center; gap: 10px; }
.peer-name { font-size: 16px; font-weight: 600; color: #303133; }

.messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  min-height: 380px;
  background: #f9f9f9;
}
.msg-item { margin-bottom: 14px; }
.msg-item.me { text-align: right; }
.bubble {
  display: inline-block;
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fff;
  color: #303133;
  text-align: left;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}
.msg-item.me .bubble { background: #409eff; color: #fff; }
.msg-item .time { font-size: 11px; color: #909399; margin-top: 4px; }
.no-msg { text-align: center; color: #909399; padding: 40px; }

.input-area {
  border-top: 1px solid #e4e7ed;
  padding: 12px 16px;
  background: #fff;
  border-radius: 0 0 10px 10px;
}
.input-actions { margin-top: 10px; text-align: right; }

@media (max-width: 900px) {
  .chat-layout { grid-template-columns: 1fr; }
  .conversation-list { display: none; }
}
</style>