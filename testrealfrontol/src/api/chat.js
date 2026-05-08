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
