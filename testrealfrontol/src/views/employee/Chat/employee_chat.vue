<template>
  <div class="chat-page">
    <el-card class="chat-card" shadow="hover">
      <template #header>
        <div class="chat-header">
          <h2>{{ $t('empChat.title') }}</h2>
          <div class="header-actions">
            <el-button @click="loadConversations" :loading="loadingConversations">{{ $t('empChat.refreshConversations') }}</el-button>
          </div>
        </div>
      </template>

      <div class="chat-layout">
        <aside class="conversation-list" v-loading="loadingConversations">
          <div class="tool-row">
            <el-input v-model="searchKeyword" :placeholder="$t('empChat.searchPlaceholder')" clearable @keyup.enter="searchUsers">
              <template #append>
                <el-button @click="searchUsers">{{ $t('empChat.search') }}</el-button>
              </template>
            </el-input>
          </div>

          <div class="search-result" v-if="searchResults.length">
            <div class="result-title">{{ $t('empChat.searchResults') }}</div>
            <div class="result-item" v-for="u in searchResults" :key="`${u.role}-${u.number}`">
              <div>
                <b>{{ u.name }}</b>
                <span class="sub">{{ u.number }} / {{ roleText(u.role) }}</span>
              </div>
              <el-button size="small" type="primary" link @click="addFriend(u)">{{ $t('empChat.addFriend') }}</el-button>
            </div>
          </div>

          <div class="search-result" v-if="friendRequests.length">
            <div class="result-title">{{ $t('empChat.friendRequests') }}</div>
            <div class="result-item" v-for="r in friendRequests" :key="r.id">
              <div>
                <b>{{ r.owner_name }}</b>
                <span class="sub">{{ r.owner_number }} / {{ roleText(r.owner_role) }}</span>
              </div>
              <div>
                <el-button size="small" type="success" link @click="respondFriend(r, 'accept')">{{ $t('empChat.accept') }}</el-button>
                <el-button size="small" type="danger" link @click="respondFriend(r, 'reject')">{{ $t('empChat.reject') }}</el-button>
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
              <span class="last">{{ item.last_message || $t('empChat.noMessages') }}</span>
              <el-badge v-if="item.unread_count > 0" :value="item.unread_count" class="badge" />
            </div>
          </div>

          <el-empty v-if="!conversations.length && !loadingConversations" :description="$t('empChat.noConversations')" :image-size="80" />
        </aside>

        <section class="message-panel">
          <div v-if="!activePeer" class="empty-wrap">
            <el-empty :description="$t('empChat.selectConversation')" />
          </div>

          <template v-else>
            <div class="peer-header">
              <div>
                <b>{{ activePeer.peer_name || activePeer.peer_number }}</b>
                <span class="sub">（{{ roleText(activePeer.peer_role) }}）</span>
              </div>
              <el-button size="small" @click="loadMessages">{{ $t('empChat.refreshMessages') }}</el-button>
            </div>

            <div class="message-list" ref="messageListRef" v-loading="loadingMessages">
              <div v-for="msg in messages" :key="msg.id" class="msg-row" :class="{ me: msg.is_me }">
                <div class="bubble">{{ msg.content }}</div>
                <div class="meta">{{ msg.created_at }}</div>
              </div>
              <el-empty v-if="!messages.length && !loadingMessages" :description="$t('empChat.noMessages')" :image-size="70" />
            </div>

            <div v-if="peerTyping" class="typing-indicator">
              {{ activePeer.peer_name || activePeer.peer_number }} {{ $t('empChat.typing') || 'is typing...' }}
            </div>
            <div class="composer">
              <el-input
                v-model="draft"
                type="textarea"
                :rows="3"
                maxlength="3000"
                show-word-limit
                :placeholder="$t('empChat.inputMessage')"
                @keydown.ctrl.enter="sendMessage"
              />
              <div class="composer-actions">
                <el-button type="primary" :loading="sending" @click="sendMessage">{{ $t('empChat.send') }}</el-button>
              </div>
            </div>
          </template>
        </section>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  getConversations,
  getMessages,
  sendMessage as httpSendMessage,
  markRead as httpMarkRead,
  searchUsers as searchUsersApi,
  addFriend as httpAddFriend,
  getFriendRequests,
  respondFriend as httpRespondFriend
} from '@/api/chat'
import { useUserStore } from '@/stores/userStore'
import {
  connectSocket,
  disconnectSocket,
  isSocketConnected,
  joinChat,
  sendMessage as socketSendMessage,
  onNewMessage,
  onTyping,
  onMessagesRead,
  markAsRead,
  emitTyping,
  offAllChatEvents,
} from '@/utils/socket'

const { t } = useI18n()
const userStore = useUserStore()

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

// Typing indicator state
const peerTyping = ref(false)
let typingTimeout = null
let pollInterval = null

const roleText = (role) => (role === 'admin' ? t('empChat.admin') : t('empChat.employee'))

const scrollBottom = async () => {
  await nextTick()
  const el = messageListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

/* ------------------------------------------------------------------ */
/*  Polling fallback                                                   */
/* ------------------------------------------------------------------ */

const startPolling = () => {
  stopPolling()
  pollInterval = setInterval(async () => {
    await loadConversations()
    if (activePeer.value) await loadMessages()
  }, 30000)
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

/* ------------------------------------------------------------------ */
/*  HTTP data loaders (initial + fallback)                             */
/* ------------------------------------------------------------------ */

const loadConversations = async () => {
  loadingConversations.value = true
  try {
    const { data } = await getConversations()
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
    const { data } = await getMessages({
      peer_number: activePeer.value.peer_number,
      peer_role: activePeer.value.peer_role,
      limit: 150
    })
    messages.value = data?.data || []
    await markReadHTTP()
    await scrollBottom()
  } catch (_e) {
    messages.value = []
  } finally {
    loadingMessages.value = false
  }
}

const markReadHTTP = async () => {
  if (!activePeer.value) return
  try {
    await httpMarkRead({
      peer_number: activePeer.value.peer_number,
      peer_role: activePeer.value.peer_role
    })
  } catch (_e) {}
}

/* ------------------------------------------------------------------ */
/*  Conversation / friend management                                   */
/* ------------------------------------------------------------------ */

const selectConversation = async (item) => {
  activePeer.value = {
    peer_number: item.peer_number,
    peer_role: item.peer_role,
    peer_name: item.peer_name
  }
  await loadMessages()
  await loadConversations()
  // Notify the server via socket that we've read this conversation
  if (isSocketConnected()) {
    markAsRead({ peerNumber: item.peer_number, peerRole: item.peer_role })
  }
}

const searchUsers = async () => {
  const kw = (searchKeyword.value || '').trim()
  if (!kw) {
    searchResults.value = []
    return
  }
  try {
    const { data } = await searchUsersApi({ keyword: kw })
    searchResults.value = data?.data || []
  } catch (_e) {
    searchResults.value = []
  }
}

const addFriend = async (u) => {
  try {
    const { data } = await httpAddFriend({
      friend_number: u.number,
      friend_role: u.role
    })
    if (data?.status) {
      ElMessage.success(data?.msg || t('empChat.requestSent'))
      await loadConversations()
    } else {
      ElMessage.error(data?.msg || t('empChat.requestFailed'))
    }
  } catch (_e) {
    ElMessage.error(t('empChat.requestFailed'))
  }
}

const loadFriendRequests = async () => {
  try {
    const { data } = await getFriendRequests()
    friendRequests.value = data?.data || []
  } catch (_e) {
    friendRequests.value = []
  }
}

const respondFriend = async (r, action) => {
  try {
    const { data } = await httpRespondFriend({
      request_id: r.id,
      action
    })
    if (data?.status) {
      ElMessage.success(data?.msg || t('empChat.operationSuccess'))
      await loadFriendRequests()
      await loadConversations()
    } else {
      ElMessage.error(data?.msg || t('empChat.operationFailed'))
    }
  } catch (_e) {
    ElMessage.error(t('empChat.operationFailed'))
  }
}

/* ------------------------------------------------------------------ */
/*  Send message (socket-first, HTTP fallback)                         */
/* ------------------------------------------------------------------ */

const sendMessage = async () => {
  if (!activePeer.value) {
    ElMessage.warning(t('empChat.selectConversationFirst'))
    return
  }
  const content = (draft.value || '').trim()
  if (!content) {
    ElMessage.warning(t('empChat.messageEmpty'))
    return
  }
  sending.value = true
  try {
    if (isSocketConnected()) {
      await socketSendMessage({
        toUserNumber: activePeer.value.peer_number,
        toUserRole: activePeer.value.peer_role,
        content,
      })
      draft.value = ''
      // Optimistically append our own message
      messages.value.push({
        id: Date.now(),
        content,
        created_at: new Date().toLocaleString(),
        is_me: true,
      })
      await scrollBottom()
      await loadConversations()
    } else {
      // Fallback to HTTP
      const { data } = await httpSendMessage({
        receiver_number: activePeer.value.peer_number,
        receiver_role: activePeer.value.peer_role,
        content
      })
      if (data?.status) {
        draft.value = ''
        await loadMessages()
        await loadConversations()
      } else {
        ElMessage.error(data?.msg || t('empChat.sendFailed'))
      }
    }
  } catch (_e) {
    ElMessage.error(t('empChat.sendFailed'))
  } finally {
    sending.value = false
  }
}

/* ------------------------------------------------------------------ */
/*  Typing indicator                                                   */
/* ------------------------------------------------------------------ */

const onInputTyping = () => {
  if (!activePeer.value || !isSocketConnected()) return
  emitTyping({ toUserNumber: activePeer.value.peer_number })
}

// Watch draft for typing events (debounced)
let draftTypingTimer = null
watch(draft, () => {
  if (draftTypingTimer) clearTimeout(draftTypingTimer)
  draftTypingTimer = setTimeout(onInputTyping, 500)
})

/* ------------------------------------------------------------------ */
/*  Socket setup                                                       */
/* ------------------------------------------------------------------ */

const setupSocketListeners = () => {
  // Cleanup existing listeners to avoid duplicates
  offAllChatEvents()

  onNewMessage((msg) => {
    if (activePeer.value) {
      const isFromActivePeer =
        msg.sender_number === activePeer.value.peer_number &&
        msg.sender_role === activePeer.value.peer_role
      const isToMe = msg.receiver_number === userStore.user_number

      if (isFromActivePeer && isToMe) {
        messages.value.push({
          id: msg.id,
          content: msg.content,
          created_at: msg.created_at,
          is_me: false,
        })
        scrollBottom()
        markAsRead({
          peerNumber: activePeer.value.peer_number,
          peerRole: activePeer.value.peer_role,
        })
      }
    }
    loadConversations()
  })

  onTyping((data) => {
    if (!activePeer.value) return
    if (data.from_user_number === activePeer.value.peer_number) {
      peerTyping.value = true
      if (typingTimeout) clearTimeout(typingTimeout)
      typingTimeout = setTimeout(() => {
        peerTyping.value = false
      }, 3000)
    }
  })

  onMessagesRead(() => {
    loadConversations()
  })
}

const initChat = async () => {
  await Promise.all([loadConversations(), loadFriendRequests()])

  const token = userStore.token
  if (!token) return

  connectSocket(token, {
    onAuthenticated (data) {
      if (data.user_number) {
        joinChat(data.user_number)
      }
      // Socket connected -- stop polling fallback
      stopPolling()
      setupSocketListeners()
    },
  })

  // If socket doesn't connect within 5 seconds, start polling fallback
  setTimeout(() => {
    if (!isSocketConnected()) {
      ElMessage.warning(t('empChat.socketFallback') || 'Real-time connection unavailable, using polling')
      startPolling()
    }
  }, 5000)
}

onMounted(initChat)

onBeforeUnmount(() => {
  offAllChatEvents()
  stopPolling()
  if (typingTimeout) clearTimeout(typingTimeout)
  if (draftTypingTimer) clearTimeout(draftTypingTimer)
  disconnectSocket()
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
.typing-indicator { padding: 4px 0 6px; font-size: 12px; color: #909399; font-style: italic; }
.composer { border-top: 1px solid #ebeef5; padding-top: 10px; }
.composer-actions { margin-top: 8px; display: flex; justify-content: flex-end; }

@media (max-width: 1100px) {
  .chat-layout { grid-template-columns: 1fr; }
}
</style>
