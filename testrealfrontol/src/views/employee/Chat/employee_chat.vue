<template>
  <div class="chat-page">
    <el-card class="chat-card" shadow="hover">
      <template #header>
        <div class="chat-header">
          <h2>在线沟通</h2>
          <div class="header-actions">
            <el-button @click="loadConversations" :loading="loadingConversations">刷新会话</el-button>
          </div>
        </div>
      </template>

      <div class="chat-layout">
        <aside class="conversation-list" v-loading="loadingConversations">
          <div class="tool-row">
            <el-input v-model="searchKeyword" placeholder="按账号/姓名搜索" clearable @keyup.enter="searchUsers">
              <template #append>
                <el-button @click="searchUsers">搜索</el-button>
              </template>
            </el-input>
          </div>

          <div class="search-result" v-if="searchResults.length">
            <div class="result-title">搜索结果</div>
            <div class="result-item" v-for="u in searchResults" :key="`${u.role}-${u.number}`">
              <div>
                <b>{{ u.name }}</b>
                <span class="sub">{{ u.number }} / {{ roleText(u.role) }}</span>
              </div>
              <el-button size="small" type="primary" link @click="addFriend(u)">申请好友</el-button>
            </div>
          </div>

          <div class="search-result" v-if="friendRequests.length">
            <div class="result-title">收到的好友申请</div>
            <div class="result-item" v-for="r in friendRequests" :key="r.id">
              <div>
                <b>{{ r.owner_name }}</b>
                <span class="sub">{{ r.owner_number }} / {{ roleText(r.owner_role) }}</span>
              </div>
              <div>
                <el-button size="small" type="success" link @click="respondFriend(r, 'accept')">同意</el-button>
                <el-button size="small" type="danger" link @click="respondFriend(r, 'reject')">拒绝</el-button>
              </div>
            </div>
          </div>

          <div
            v-for="item in conversations"
            :key="`${item.peer_role}-${item.peer_number}`"
            class="conversation-item"
            :class="{ active: activePeer && activePeer.peer_number === item.peer_number && activePeer.peer_role === item.peer_role }"
            @click="selectConversation(item)"
          >
            <div class="top-row">
              <span class="name">{{ item.peer_name || item.peer_number }}</span>
              <span class="time">{{ item.last_time || '' }}</span>
            </div>
            <div class="bottom-row">
              <span class="last">{{ item.last_message || '暂无消息' }}</span>
              <el-badge v-if="item.unread_count > 0" :value="item.unread_count" class="badge" />
            </div>
          </div>

          <el-empty v-if="!conversations.length && !loadingConversations" description="暂无会话" :image-size="80" />
        </aside>

        <section class="message-panel">
          <div v-if="!activePeer" class="empty-wrap">
            <el-empty description="请选择左侧会话，或搜索并添加联系人" />
          </div>

          <template v-else>
            <div class="peer-header">
              <div>
                <b>{{ activePeer.peer_name || activePeer.peer_number }}</b>
                <span class="sub">（{{ roleText(activePeer.peer_role) }}）</span>
              </div>
              <el-button size="small" @click="loadMessages">刷新消息</el-button>
            </div>

            <div class="message-list" ref="messageListRef" v-loading="loadingMessages">
              <div v-for="msg in messages" :key="msg.id" class="msg-row" :class="{ me: msg.is_me }">
                <div class="bubble">{{ msg.content }}</div>
                <div class="meta">{{ msg.created_at }}</div>
              </div>
              <el-empty v-if="!messages.length && !loadingMessages" description="暂无消息" :image-size="70" />
            </div>

            <div class="composer">
              <el-input
                v-model="draft"
                type="textarea"
                :rows="3"
                maxlength="3000"
                show-word-limit
                placeholder="请输入消息内容"
                @keydown.ctrl.enter="sendMessage"
              />
              <div class="composer-actions">
                <el-button type="primary" :loading="sending" @click="sendMessage">发送（Ctrl+Enter）</el-button>
              </div>
            </div>
          </template>
        </section>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import Axios from '@/utils/Axios'

const conversations = ref([])
const messages = ref([])
const activePeer = ref(null)
const draft = ref('')
const searchKeyword = ref('')
const searchResults = ref([])
const friendRequests = ref([])

const loadingConversations = ref(false)
const loadingMessages = ref(false)
const sending = ref(false)
const messageListRef = ref(null)

let pollTimer = null

const roleText = (role) => (role === 'admin' ? '管理员' : '员工')

const scrollBottom = async () => {
  await nextTick()
  const el = messageListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

const loadConversations = async () => {
  loadingConversations.value = true
  try {
    const { data } = await Axios.get(`/api/chat/conversations`)
    conversations.value = data?.data || []
  } catch (_e) {
    conversations.value = []
  } finally {
    loadingConversations.value = false
  }
}

const loadMessages = async () => {
  if (!activePeer.value) return
  loadingMessages.value = true
  try {
    const { data } = await Axios.get(`/api/chat/messages`, {
      params: {
        peer_number: activePeer.value.peer_number,
        peer_role: activePeer.value.peer_role,
        limit: 150
      }
    })
    messages.value = data?.data || []
    await markRead()
    await scrollBottom()
  } catch (_e) {
    messages.value = []
  } finally {
    loadingMessages.value = false
  }
}

const markRead = async () => {
  if (!activePeer.value) return
  try {
    await Axios.post(`/api/chat/mark_read`, {
      peer_number: activePeer.value.peer_number,
      peer_role: activePeer.value.peer_role
    })
  } catch (_e) {}
}

const selectConversation = async (item) => {
  activePeer.value = {
    peer_number: item.peer_number,
    peer_role: item.peer_role,
    peer_name: item.peer_name
  }
  await loadMessages()
  await loadConversations()
}

const searchUsers = async () => {
  const kw = (searchKeyword.value || '').trim()
  if (!kw) {
    searchResults.value = []
    return
  }
  try {
    const { data } = await Axios.get(`/api/chat/search_users`, { params: { keyword: kw } })
    searchResults.value = data?.data || []
  } catch (_e) {
    searchResults.value = []
  }
}

const addFriend = async (u) => {
  try {
    const { data } = await Axios.post(`/api/chat/add_friend`, {
      friend_number: u.number,
      friend_role: u.role
    })
    if (data?.status) {
      ElMessage.success(data?.msg || '申请已发送')
      await loadConversations()
    } else {
      ElMessage.error(data?.msg || '申请失败')
    }
  } catch (_e) {
    ElMessage.error('申请失败')
  }
}

const loadFriendRequests = async () => {
  try {
    const { data } = await Axios.get(`/api/chat/friend_requests`)
    friendRequests.value = data?.data || []
  } catch (_e) {
    friendRequests.value = []
  }
}

const respondFriend = async (r, action) => {
  try {
    const { data } = await Axios.post(`/api/chat/friend_respond`, {
      request_id: r.id,
      action
    })
    if (data?.status) {
      ElMessage.success(data?.msg || '操作成功')
      await loadFriendRequests()
      await loadConversations()
    } else {
      ElMessage.error(data?.msg || '操作失败')
    }
  } catch (_e) {
    ElMessage.error('操作失败')
  }
}

const sendMessage = async () => {
  if (!activePeer.value) {
    ElMessage.warning('请先选择会话')
    return
  }
  const content = (draft.value || '').trim()
  if (!content) {
    ElMessage.warning('消息不能为空')
    return
  }
  sending.value = true
  try {
    const { data } = await Axios.post(`/api/chat/send`, {
      receiver_number: activePeer.value.peer_number,
      receiver_role: activePeer.value.peer_role,
      content
    })
    if (data?.status) {
      draft.value = ''
      await loadMessages()
      await loadConversations()
    } else {
      ElMessage.error(data?.msg || '发送失败')
    }
  } catch (_e) {
    ElMessage.error('发送失败')
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadConversations(), loadFriendRequests()])
  document.addEventListener('visibilitychange', handleVisibilityChange)
  startPolling()
})

const startPolling = () => {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (document.visibilityState === 'visible') {
      await Promise.all([loadConversations(), loadFriendRequests()])
      if (activePeer.value) await loadMessages()
    }
  }, 30000) // 改为30秒
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    loadConversations()
    loadFriendRequests()
    if (activePeer.value) loadMessages()
  }
}

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.chat-page { padding: 20px; }
.chat-card { border-radius: 12px; }
.chat-header { display: flex; justify-content: space-between; align-items: center; }
.chat-layout { display: grid; grid-template-columns: 360px 1fr; gap: 14px; min-height: 640px; }
.conversation-list { border: 1px solid #ebeef5; border-radius: 10px; padding: 8px; overflow-y: auto; }
.tool-row { margin-bottom: 10px; }
.search-result { border: 1px dashed #dcdfe6; border-radius: 8px; padding: 8px; margin-bottom: 10px; }
.result-title { font-size: 12px; color: #909399; margin-bottom: 6px; }
.result-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 2px; }
.conversation-item { padding: 10px; border-radius: 8px; cursor: pointer; margin-bottom: 8px; border: 1px solid transparent; }
.conversation-item:hover { background: #f5f7fa; }
.conversation-item.active { border-color: #409eff; background: #ecf5ff; }
.top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.name { font-weight: 600; color: #303133; }
.time { color: #909399; font-size: 12px; }
.bottom-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.last { color: #606266; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 240px; }
.message-panel { border: 1px solid #ebeef5; border-radius: 10px; padding: 10px; display: flex; flex-direction: column; }
.empty-wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; }
.peer-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid #ebeef5; }
.sub { color: #909399; margin-left: 4px; font-size: 12px; }
.message-list { flex: 1; overflow-y: auto; padding: 12px 0; min-height: 420px; }
.msg-row { display: flex; flex-direction: column; margin-bottom: 12px; align-items: flex-start; }
.msg-row.me { align-items: flex-end; }
.bubble { max-width: 70%; padding: 10px 12px; border-radius: 8px; background: #f2f6fc; color: #303133; white-space: pre-wrap; word-break: break-word; }
.msg-row.me .bubble { background: #409eff; color: #fff; }
.meta { margin-top: 4px; font-size: 12px; color: #909399; }
.composer { border-top: 1px solid #ebeef5; padding-top: 10px; }
.composer-actions { margin-top: 8px; display: flex; justify-content: flex-end; }

@media (max-width: 1100px) {
  .chat-layout { grid-template-columns: 1fr; }
}
</style>
