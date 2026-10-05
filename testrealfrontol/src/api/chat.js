/**
 * @module api/chat
 * Chat operations — conversations, messages, friend management
 */
import axios from '@/utils/Axios'

/**
 * Get all conversations for the current user.
 * @returns {Promise<AxiosResponse>}
 */
export const getConversations = () => axios.get('/api/chat/conversations')

/**
 * Get messages for a conversation.
 * @param {Object} params
 * @param {string} [params.conversation_id]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getMessages = (params) => axios.get('/api/chat/messages', { params })

/**
 * Send a message.
 * @param {Object} data
 * @param {string} data.conversation_id
 * @param {string} data.content
 * @returns {Promise<AxiosResponse>}
 */
export const sendMessage = (data) => axios.post('/api/chat/send', data)

/**
 * Mark messages as read.
 * @param {Object} data
 * @param {string} data.conversation_id
 * @returns {Promise<AxiosResponse>}
 */
export const markRead = (data) => axios.post('/api/chat/mark-read', data)

/**
 * Search users by keyword.
 * @param {Object} params
 * @param {string} params.keyword
 * @returns {Promise<AxiosResponse>}
 */
export const searchUsers = (params) => axios.get('/api/chat/search-users', { params })

/**
 * Send a friend request.
 * @param {Object} data
 * @param {string} data.target_user_number
 * @returns {Promise<AxiosResponse>}
 */
export const addFriend = (data) => axios.post('/api/chat/add-friend', data)

/**
 * Get pending friend requests.
 * @returns {Promise<AxiosResponse>}
 */
export const getFriendRequests = () => axios.get('/api/chat/friend-requests')

/**
 * Respond to a friend request (accept/reject).
 * @param {Object} data
 * @param {string} data.request_id
 * @param {boolean} data.accept
 * @returns {Promise<AxiosResponse>}
 */
export const respondFriend = (data) => axios.post('/api/chat/friend-respond', data)

/**
 * Send a message to the AI assistant.
 * @param {Object} data
 * @param {string} data.message - User message
 * @param {Array} [data.history] - Conversation history [{role, content}]
 * @returns {Promise<AxiosResponse>}
 */
export const sendAIMessage = (data) => axios.post('/api/ai/chat', data)

/**
 * Send a message to the AI assistant via SSE streaming.
 * Uses fetch() directly for SSE support (axios doesn't handle SSE well).
 * @param {Object} data
 * @param {string} data.message - User message
 * @param {Array} [data.history] - Conversation history [{role, content}]
 * @param {Function} onToken - Callback for each token: (token: string) => void
 * @param {Function} onDone - Callback when stream completes: () => void
 * @param {Function} onError - Callback on error: (error: Error) => void
 * @returns {AbortController} - Call controller.abort() to cancel the stream
 */
export const sendAIMessageStream = (data, onToken, onDone, onError) => {
  const controller = new AbortController()
  const token = sessionStorage.getItem('token') || localStorage.getItem('token')

  fetch('/api/ai/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
    signal: controller.signal,
  })
    .then(async (resp) => {
      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({}))
        throw new Error(errBody.msg || `HTTP ${resp.status}`)
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const payload = JSON.parse(line.slice(6))
            if (payload.token) onToken(payload.token)
            if (payload.done) { onDone(); return }
            if (payload.error) throw new Error(payload.error)
          } catch (e) {
            if (e.message && !e.message.includes('JSON')) throw e
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err)
    })

  return controller
}
