/**
 * Socket.IO client singleton for real-time chat.
 *
 * Usage:
 *   import { connectSocket, joinChat, sendMessage, onNewMessage, onTyping, emitTyping, markAsRead, onMessagesRead, disconnectSocket } from '@/utils/socket'
 *
 * The module re-uses a single connection and automatically re-authenticates
 * after reconnection.  All helpers are safe to call even when the socket is
 * not connected -- they will silently no-op in that case.
 */

import { io } from 'socket.io-client'
import { ElMessage } from 'element-plus'

let socket = null
let _authenticated = false
let _joinedRooms = new Set()

/* ------------------------------------------------------------------ */
/*  Connection management                                              */
/* ------------------------------------------------------------------ */

/**
 * Connect and authenticate the Socket.IO client.
 * Returns the socket instance (or null if no token).
 *
 * @param {string} token - JWT access token
 * @param {object} [opts] - extra options
 * @param {Function} [opts.onAuthenticated] - callback after successful auth
 */
export function connectSocket (token, opts = {}) {
  if (!token) return null

  // Re-use existing connected socket
  if (socket && socket.connected) return socket

  if (!socket) {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5003'
    socket = io(apiUrl, {
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 2000,
      reconnectionDelayMax: 10000,
    })

    socket.on('connect', () => {
      _authenticated = false
      socket.emit('authenticate', { token })
    })

    socket.on('authenticated', (data) => {
      if (data.status === 'ok') {
        _authenticated = true
        // Re-join rooms after reconnection
        for (const room of _joinedRooms) {
          socket.emit('join_chat', { user_number: room })
        }
        if (opts.onAuthenticated) opts.onAuthenticated(data)
      } else {
        ElMessage.warning(data.msg || 'WebSocket authentication failed')
      }
    })

    socket.on('disconnect', () => {
      _authenticated = false
    })

    socket.on('connect_error', () => {
      // Silently retry -- the user will see a fallback to polling
    })
  } else {
    // Socket exists but was disconnected -- update token and reconnect
    socket.auth = { token }
    socket.connect()
  }

  return socket
}

/**
 * Gracefully disconnect the socket.
 */
export function disconnectSocket () {
  if (socket) {
    socket.disconnect()
    socket = null
    _authenticated = false
    _joinedRooms.clear()
  }
}

/**
 * Whether the socket is currently connected and authenticated.
 */
export function isSocketConnected () {
  return !!(socket && socket.connected && _authenticated)
}

/* ------------------------------------------------------------------ */
/*  Chat helpers                                                       */
/* ------------------------------------------------------------------ */

/**
 * Join the user's personal chat room so they can receive messages.
 */
export function joinChat (userNumber) {
  if (!userNumber) return
  _joinedRooms.add(String(userNumber))
  if (socket && socket.connected) {
    socket.emit('join_chat', { user_number: String(userNumber) })
  }
}

/**
 * Send a chat message via Socket.IO.
 * The server will persist it and relay it to the recipient.
 *
 * @param {object} params
 * @param {string} params.toUserNumber
 * @param {string} params.toUserRole
 * @param {string} params.content
 * @returns {Promise} resolves on 'message_sent', rejects on 'send_message_error'
 */
export function sendMessage ({ toUserNumber, toUserRole, content }) {
  return new Promise((resolve, reject) => {
    if (!socket || !socket.connected) {
      reject(new Error('Socket not connected'))
      return
    }
    socket.emit('send_message', {
      to_user_number: toUserNumber,
      to_user_role: toUserRole,
      content,
    })

    const onSent = (data) => {
      cleanup()
      resolve(data)
    }
    const onErr = (data) => {
      cleanup()
      reject(new Error(data?.msg || 'Send failed'))
    }
    const cleanup = () => {
      socket.off('message_sent', onSent)
      socket.off('send_message_error', onErr)
    }
    socket.once('message_sent', onSent)
    socket.once('send_message_error', onErr)

    // Timeout fallback
    setTimeout(() => {
      cleanup()
      reject(new Error('Send timeout'))
    }, 10000)
  })
}

/**
 * Mark messages from a peer as read via Socket.IO.
 */
export function markAsRead ({ peerNumber, peerRole }) {
  if (!socket || !socket.connected) return
  socket.emit('mark_read', {
    peer_number: peerNumber,
    peer_role: peerRole,
  })
}

/**
 * Emit a typing indicator to the recipient.
 */
export function emitTyping ({ toUserNumber }) {
  if (!socket || !socket.connected) return
  socket.emit('typing', {
    to_user_number: toUserNumber,
  })
}

/* ------------------------------------------------------------------ */
/*  Event listeners                                                    */
/* ------------------------------------------------------------------ */

/**
 * Register a callback for incoming messages.
 * @param {Function} callback - receives the message payload
 * @returns {Function} unsubscribe function
 */
export function onNewMessage (callback) {
  if (!socket) return () => {}
  socket.on('new_message', callback)
  return () => socket.off('new_message', callback)
}

/**
 * Register a callback for typing indicators.
 * @param {Function} callback - receives { from_user_number, from_user_role }
 * @returns {Function} unsubscribe function
 */
export function onTyping (callback) {
  if (!socket) return () => {}
  socket.on('typing', callback)
  return () => socket.off('typing', callback)
}

/**
 * Register a callback for messages_read (peer read our messages).
 * @param {Function} callback
 * @returns {Function} unsubscribe function
 */
export function onMessagesRead (callback) {
  if (!socket) return () => {}
  socket.on('messages_read', callback)
  return () => socket.off('messages_read', callback)
}

/**
 * Remove all chat-related listeners.  Useful on component unmount.
 */
export function offAllChatEvents () {
  if (!socket) return
  socket.off('new_message')
  socket.off('typing')
  socket.off('messages_read')
  socket.off('message_read')
}
