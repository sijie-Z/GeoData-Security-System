<template>
  <div class="chat-page">
    <el-card class="chat-card" shadow="hover">
      <template #header>
        <div class="chat-header">
          <div class="header-left">
            <el-radio-group v-model="activeTab" size="default">
              <el-radio-button value="human">💬 {{ $t('empChat.humanChat') || '人工聊天' }}</el-radio-button>
              <el-radio-button value="ai">🤖 {{ $t('empChat.aiAssistant') || 'AI 助手' }}</el-radio-button>
            </el-radio-group>
          </div>
          <div class="header-actions" v-if="activeTab === 'human'">
            <el-button @click="loadConversations" :loading="loadingConversations">{{ $t('empChat.refreshConversations') }}</el-button>
          </div>
        </div>
      </template>

      <!-- ==================== AI 助手 ==================== -->
      <div v-if="activeTab === 'ai'" class="ai-layout">
        <aside class="ai-conv-list">
          <div class="ai-conv-toolbar">
            <el-button size="small" type="primary" @click="newAIConversation" style="width:100%">
              + {{ $t('empChat.newConversation') || '新对话' }}
            </el-button>
          </div>
          <div class="ai-conv-items">
            <div
              v-for="conv in aiConversations"
              :key="conv.id"
              class="ai-conv-item"
              :class="{ active: conv.id === activeAIConvId }"
              @click="switchAIConversation(conv.id)"
            >
              <div class="ai-conv-title">
                <span style="margin-right:4px">💬</span>
                <span class="ai-conv-text">{{ conv.title || $t('empChat.newConversation') || '新对话' }}</span>
              </div>
              <div class="ai-conv-meta">
                <span class="ai-conv-msg-count">{{ conv.messages.length }} 条</span>
                <el-button
                  v-if="aiConversations.length > 1"
                  text
                  size="small"
                  type="danger"
                  @click.stop="deleteAIConversation(conv.id)"
                  class="ai-conv-del"
                  style="font-size:14px;padding:0 4px;min-height:auto"
                >✕</el-button>
              </div>
            </div>
            <el-empty v-if="!aiConversations.length" :description="$t('empChat.noConversations') || '暂无对话'" :image-size="60" />
          </div>
        </aside>

        <div class="ai-main" style="display:flex;flex-direction:column">
          <div class="ai-messages" ref="aiMessageListRef">
            <!-- 欢迎消息 -->
            <div v-if="!aiMessages.length" class="ai-welcome">
              <div class="ai-welcome-icon">🤖</div>
              <h3>{{ $t('empChat.aiWelcomeTitle') || '你好！我是地安智助' }}</h3>
              <p>{{ $t('empChat.aiWelcomeDesc') || '我可以帮你解答关于系统使用、数据申请、水印技术等问题。' }}</p>
              <div class="ai-suggestions">
                <el-button v-for="q in aiSuggestions" :key="q" text class="suggestion-btn" @click="askSuggestion(q)">
                  {{ q }}
                </el-button>
              </div>
            </div>

            <div v-for="(msg, idx) in aiMessages" :key="idx" class="msg-row" :class="{ me: msg.role === 'user' }">
              <div class="bubble" :class="{ 'ai-bubble': msg.role === 'assistant' }">
                <div class="bubble-role" style="font-size:12px;margin-bottom:2px">{{ msg.role === 'assistant' ? '🤖 AI' : '👤 我' }}</div>
                <div v-if="msg.loading" class="ai-typing">
                  <span class="motion-loop"></span><span class="motion-loop"></span><span class="motion-loop"></span>
                </div>
                <template v-else>{{ msg.content }}</template>
              </div>
            </div>
          </div>

          <div class="composer">
            <el-input
              v-model="aiDraft"
              type="textarea"
              :rows="2"
              maxlength="2000"
              show-word-limit
              :placeholder="$t('empChat.aiPlaceholder') || '输入你的问题，例如：如何申请数据？'"
              @keydown.enter.exact.prevent="sendAIMessage"
            />
            <div class="composer-actions">
              <el-button @click="clearAIChat" text>{{ $t('empChat.aiClear') || '清空对话' }}</el-button>
              <el-button type="primary" :loading="aiSending" @click="sendAIMessage">
                {{ $t('empChat.aiSend') || '发送' }}
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 人工聊天 ==================== -->
      <div v-else class="chat-layout">
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
import { nextTick, onBeforeUnmount, onMounted, ref, computed } from 'vue'
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
  respondFriend as httpRespondFriend,
  sendAIMessageStream
} from '@/api/chat'

const { t } = useI18n()

// ── Tab 切换 ──
const activeTab = ref('human')

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

let pollInterval = null

// ── AI 助手状态 ──
const STORAGE_KEY = 'ai_conversations'
const aiConversations = ref([])
const activeAIConvId = ref(null)
const aiDraft = ref('')
const aiSending = ref(false)
const aiMessageListRef = ref(null)
let aiAbortController = null
const aiSuggestions = [
  '如何申请数据？',
  '数字水印是怎么工作的？',
  '申请审批流程是什么？',
  '如何成为管理员？',
]

// 从 localStorage 加载 AI 对话记录
function loadAIConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      aiConversations.value = JSON.parse(raw)
      // 自动选中最近一个对话
      if (aiConversations.value.length > 0) {
        activeAIConvId.value = aiConversations.value[0].id
      }
    }
  } catch (_) { /* ignore */ }
}

// 保存 AI 对话到 localStorage
function saveAIConversations() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(aiConversations.value))
  } catch (_) { /* ignore */ }
}

// 当前活跃对话的消息列表（computed）
const aiMessages = computed({
  get() {
    const conv = aiConversations.value.find(c => c.id === activeAIConvId.value)
    return conv ? conv.messages : []
  },
  set(newMsgs) {
    const conv = aiConversations.value.find(c => c.id === activeAIConvId.value)
    if (conv) {
      conv.messages = newMsgs
      saveAIConversations()
    }
  }
})

// 生成唯一 ID
function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}

// 新建对话
function newAIConversation() {
  const conv = {
    id: genId(),
    title: '',
    messages: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  aiConversations.value.unshift(conv)
  activeAIConvId.value = conv.id
  aiDraft.value = ''
  saveAIConversations()
}

// 切换对话
function switchAIConversation(id) {
  if (aiSending.value) return
  activeAIConvId.value = id
  aiDraft.value = ''
}

// 删除对话
function deleteAIConversation(id) {
  const idx = aiConversations.value.findIndex(c => c.id === id)
  if (idx === -1) return
  aiConversations.value.splice(idx, 1)
  if (activeAIConvId.value === id) {
    activeAIConvId.value = aiConversations.value.length > 0 ? aiConversations.value[0].id : null
  }
  saveAIConversations()
}

// 更新对话标题（取第一条用户消息）
function updateConvTitle(messages) {
  const conv = aiConversations.value.find(c => c.id === activeAIConvId.value)
  if (!conv || conv.title) return
  const firstUser = messages.find(m => m.role === 'user')
  if (firstUser) {
    conv.title = firstUser.content.slice(0, 30) + (firstUser.content.length > 30 ? '...' : '')
    saveAIConversations()
  }
}

const roleText = (role) => (role === 'admin' ? t('empChat.admin') : t('empChat.employee'))

const scrollBottom = async () => {
  await nextTick()
  const el = messageListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

/* ------------------------------------------------------------------ */
/*  HTTP polling                                                       */
/* ------------------------------------------------------------------ */

const startPolling = () => {
  stopPolling()
  pollInterval = setInterval(async () => {
    await loadConversations()
    if (activePeer.value) await loadMessages()
  }, 5000)
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
  } catch (_e) { /* ignore */ }
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
/*  Send message via HTTP                                              */
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
  } catch (_e) {
    ElMessage.error(t('empChat.sendFailed'))
  } finally {
    sending.value = false
  }
}

/* ------------------------------------------------------------------ */
/*  Init — pure HTTP polling                                           */
/* ------------------------------------------------------------------ */

const initChat = async () => {
  loadAIConversations()
  if (!activeAIConvId.value && aiConversations.value.length === 0) {
    newAIConversation()
  }
  await Promise.all([loadConversations(), loadFriendRequests()])
  startPolling()
}

/* ------------------------------------------------------------------ */
/*  AI 助手                                                            */
/* ------------------------------------------------------------------ */

const scrollAIBottom = async () => {
  await nextTick()
  const el = aiMessageListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

const askSuggestion = (q) => {
  aiDraft.value = q
  sendAIMessage()
}

const sendAIMessage = async () => {
  const content = (aiDraft.value || '').trim()
  if (!content || aiSending.value) return

  // 没有活跃对话时自动新建
  if (!activeAIConvId.value) {
    newAIConversation()
  }

  const conv = aiConversations.value.find(c => c.id === activeAIConvId.value)
  if (!conv) return

  // 添加用户消息
  conv.messages.push({ role: 'user', content })
  aiDraft.value = ''
  updateConvTitle(conv.messages)
  saveAIConversations()
  await scrollAIBottom()

  // 添加 AI 占位消息
  const msgIdx = conv.messages.length
  conv.messages.push({ role: 'assistant', content: '' })
  aiSending.value = true

  // 构建历史（不含当前占位）
  const history = conv.messages
    .slice(0, -1)
    .map(m => ({ role: m.role, content: m.content }))

  aiAbortController = sendAIMessageStream(
    { message: content, history },
    // onToken
    (token) => {
      conv.messages[msgIdx].content += token
      saveAIConversations()
      scrollAIBottom()
    },
    // onDone
    () => {
      aiSending.value = false
      aiAbortController = null
      conv.updatedAt = new Date().toISOString()
      saveAIConversations()
      scrollAIBottom()
    },
    // onError
    (err) => {
      const existing = conv.messages[msgIdx].content
      conv.messages[msgIdx].content = existing
        ? existing + '\n\n⚠️ 流式响应中断'
        : '⚠️ ' + (err.message || '响应失败，请重试')
      aiSending.value = false
      aiAbortController = null
      saveAIConversations()
      scrollAIBottom()
    }
  )
}

const clearAIChat = () => {
  if (aiAbortController) {
    aiAbortController.abort()
    aiAbortController = null
  }
  aiSending.value = false
  // 清空当前对话
  const conv = aiConversations.value.find(c => c.id === activeAIConvId.value)
  if (conv) {
    conv.messages = []
    conv.title = ''
    saveAIConversations()
  }
}

onMounted(initChat)

onBeforeUnmount(() => {
  stopPolling()
  if (aiAbortController) {
    aiAbortController.abort()
    aiAbortController = null
  }
})
</script>

<style scoped>
.chat-page { padding: 20px; }
.chat-card { border-radius: 12px; }
.chat-header { display: flex; justify-content: space-between; align-items: center; }
.chat-layout { display: grid; grid-template-columns: 360px 1fr; gap: 14px; min-height: 640px; }

/* ── AI 助手样式 ── */
.ai-layout { display: grid; grid-template-columns: 280px 1fr; gap: 14px; min-height: 640px; }
.ai-main { display: flex; flex-direction: column; min-height: 640px; }
.ai-messages { flex: 1; overflow-y: auto; padding: 16px 0; min-height: 480px; }

/* AI 对话侧边栏 */
.ai-conv-list { border: 1px solid var(--border-subtle); border-radius: 10px; padding: 8px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.ai-conv-toolbar { margin-bottom: 4px; }
.ai-conv-items { flex: 1; overflow-y: auto; min-height: 200px; }
.ai-conv-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 8px; border-radius: 8px; cursor: pointer; margin-bottom: 4px; border: 1px solid transparent; transition: all 0.2s; }
.ai-conv-item:hover { background: var(--bg-hover); }
.ai-conv-item.active { border-color: var(--accent-9); background: var(--tint-info-bg); }
.ai-conv-title { display: flex; align-items: center; overflow: hidden; flex: 1; }
.ai-conv-text { font-size: 13px; color: var(--text-1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ai-conv-meta { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.ai-conv-msg-count { font-size: 11px; color: var(--text-3); }
.ai-conv-del { opacity: 0; transition: opacity 0.2s; }
.ai-conv-item:hover .ai-conv-del { opacity: 1; }
.ai-welcome { text-align: center; padding: 60px 20px; }
.ai-welcome-icon { font-size: 48px; margin-bottom: 16px; }
.ai-welcome h3 { margin: 0 0 8px; font-size: 20px; color: var(--text-1); }
.ai-welcome p { margin: 0 0 24px; color: var(--text-2); font-size: 14px; }
.ai-suggestions { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
.suggestion-btn { border: 1px solid var(--border-default); border-radius: 16px; font-size: 13px; }
.suggestion-btn:hover { border-color: var(--accent-9); color: var(--accent-9); }
.ai-bubble { background: var(--tint-success-bg) !important; color: var(--text-1) !important; }
.ai-typing { display: flex; gap: 4px; padding: 4px 0; }
.ai-typing span { width: 8px; height: 8px; border-radius: 50%; background: var(--text-3); animation: blink 1.4s infinite both; }
.ai-typing span:nth-child(2) { animation-delay: 0.2s; }
.ai-typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,80%,100% { opacity: 0.3; } 40% { opacity: 1; } }
/* §3.10 reduced-motion：AI 输入三点循环动画关闭 */
@media (prefers-reduced-motion: reduce) {
  .ai-typing span { animation: none !important; }
}
.conversation-list { border: 1px solid var(--border-subtle); border-radius: 10px; padding: 8px; overflow-y: auto; }
.tool-row { margin-bottom: 10px; }
.search-result { border: 1px dashed var(--border-default); border-radius: 8px; padding: 8px; margin-bottom: 10px; }
.result-title { font-size: 12px; color: var(--text-3); margin-bottom: 6px; }
.result-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 2px; }
.conversation-item { padding: 10px; border-radius: 8px; cursor: pointer; margin-bottom: 8px; border: 1px solid transparent; }
.conversation-item:hover { background: var(--bg-hover); }
.conversation-item.active { border-color: var(--accent-9); background: var(--tint-info-bg); }
.top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.name { font-weight: 600; color: var(--text-1); }
.time { color: var(--text-3); font-size: 12px; }
.bottom-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.last { color: var(--text-2); font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 240px; }
.message-panel { border: 1px solid var(--border-subtle); border-radius: 10px; padding: 10px; display: flex; flex-direction: column; }
.empty-wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; }
.peer-header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; border-bottom: 1px solid var(--border-subtle); }
.sub { color: var(--text-3); margin-left: 4px; font-size: 12px; }
.message-list { flex: 1; overflow-y: auto; padding: 12px 0; min-height: 420px; }
/* §3.8 AI 消息 200ms 入场（流式追加不重放：CSS animation 只在挂载触发） */
.msg-row { display: flex; flex-direction: column; margin-bottom: 12px; align-items: flex-start; animation: motion-rise var(--duration-200) var(--ease-out) both; }
.msg-row.me { align-items: flex-end; }
@media (prefers-reduced-motion: reduce) {
  .msg-row { animation: motion-fade var(--duration-150) linear both; }
}
.bubble { max-width: 70%; padding: 10px 12px; border-radius: 8px; background: var(--bg-fill); color: var(--text-1); white-space: pre-wrap; word-break: break-word; }
.bubble-role { color: var(--text-3); }
.msg-row.me .bubble { background: var(--accent-9); color: #fff; }
.meta { margin-top: 4px; font-size: 12px; color: var(--text-3); }
.composer { border-top: 1px solid var(--border-subtle); padding-top: 10px; }
.composer-actions { margin-top: 8px; display: flex; justify-content: flex-end; }

@media (max-width: 1100px) {
  .chat-layout { grid-template-columns: 1fr; }
}
</style>
