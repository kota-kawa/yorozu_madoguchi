import { useEffect, useRef, useState } from 'react'
import { apiUrl } from '../utils/apiBase'
import { getStoredUserType } from '../utils/userType'
import { consumeChatSse } from '../utils/sseChatStream'
import type { ChatApiResponse, ChatStreamFinalEvent } from '../types/api'
import type { ChatMessage, ChatMessageUpdate } from '../types/chat'

type UseGenericChatOptions = {
  initialMessage: ChatMessage
  messageEndpoint: string
  requestTimeoutMs?: number
  addSystemMessage?: boolean
}

type UseGenericChatResult = {
  messages: ChatMessage[]
  loading: boolean
  planFromChat: string
  sendMessage: (text: string) => Promise<void>
  addSystemMessage: (text: string) => void
}

const FALLBACK_ERROR_MESSAGE = 'サーバーからの応答に失敗しました。時間をおいて再試行してください。'

export const useGenericChat = ({
  initialMessage,
  messageEndpoint,
  requestTimeoutMs,
  addSystemMessage = false,
}: UseGenericChatOptions): UseGenericChatResult => {
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage])
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState('')
  const inFlightRef = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    fetch(apiUrl('/api/reset'), { method: 'POST', signal: controller.signal, credentials: 'include' }).catch(
      () => {},
    )
    return () => controller.abort()
  }, [])

  const updateMessageText = (id: string, updater: string | ((prevText: string) => string)) => {
    setMessages((prev) =>
      prev.map((message) => {
        if (message.id !== id) return message
        const nextText = typeof updater === 'function' ? updater(message.text ?? '') : updater
        return { ...message, text: nextText }
      }),
    )
  }

  const updateMessageMeta = (id: string, updates: ChatMessageUpdate) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === id ? { ...message, ...updates } : message)),
    )
  }

  const finishSending = () => {
    inFlightRef.current = false
    setLoading(false)
  }

  const sendMessage = async (text: string) => {
    if (inFlightRef.current) return

    const trimmed = text.trim()
    if (!trimmed) return

    if (trimmed.length > 3000) {
      alert('入力された文字数が3000文字を超えています。3000文字以内で入力してください。')
      return
    }

    inFlightRef.current = true

    const userMessage: ChatMessage = { id: `user-${Date.now()}`, sender: 'user', text: trimmed }
    const loadingMessageId = `bot-${Date.now()}`
    const loadingMessage: ChatMessage = {
      id: loadingMessageId,
      sender: 'bot',
      text: '考えています',
      type: 'loading',
      loading_variant: 'thinking',
      pending: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setLoading(true)

    const requestController = new AbortController()
    const timeoutId =
      typeof requestTimeoutMs === 'number' && requestTimeoutMs > 0
        ? setTimeout(() => requestController.abort(), requestTimeoutMs)
        : null

    try {
      const response = await fetch(apiUrl(messageEndpoint), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ message: trimmed, user_type: getStoredUserType(), stream: true }),
        credentials: 'include',
        signal: requestController.signal,
      })

      const contentType = response.headers.get('content-type') || ''
      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as ChatApiResponse | null
        const serverMessage = data?.response || data?.error
        throw new Error(serverMessage || `Server Error: ${response.status}`)
      }
      if (!contentType.includes('text/event-stream')) {
        throw new Error('ストリーミング応答の受信に失敗しました。')
      }

      const streamFlushIntervalMs = 30
      let bufferedText = ''
      let flushTimeoutId: ReturnType<typeof setTimeout> | null = null
      const streamState: { finalEvent: ChatStreamFinalEvent | null; usedWebSearch: boolean } = {
        finalEvent: null,
        usedWebSearch: false,
      }

      updateMessageMeta(loadingMessageId, {
        type: 'loading',
        loading_variant: 'thinking',
        pending: false,
      })

      let hasReceivedFirstChunk = false
      const flushBufferedText = () => {
        if (!bufferedText) return
        const chunkToAppend = bufferedText
        bufferedText = ''
        if (!hasReceivedFirstChunk) {
          hasReceivedFirstChunk = true
          updateMessageText(loadingMessageId, () => chunkToAppend)
        } else {
          updateMessageText(loadingMessageId, (prevText) => `${prevText}${chunkToAppend}`)
        }
      }

      await consumeChatSse(response, (event) => {
        if (event.type === 'meta') {
          streamState.usedWebSearch = Boolean(event.used_web_search)
          updateMessageMeta(loadingMessageId, {
            loading_variant: streamState.usedWebSearch ? 'web_search' : 'thinking',
          })
          return
        }
        if (event.type === 'delta') {
          if (typeof event.content === 'string' && event.content) {
            bufferedText += event.content
            if (!flushTimeoutId) {
              flushTimeoutId = setTimeout(() => {
                flushTimeoutId = null
                flushBufferedText()
              }, streamFlushIntervalMs)
            }
          }
          return
        }
        if (event.type === 'final') {
          streamState.finalEvent = event
        }
      })

      if (flushTimeoutId) {
        clearTimeout(flushTimeoutId)
        flushTimeoutId = null
      }
      flushBufferedText()

      if (!streamState.finalEvent) {
        throw new Error('ストリーミングが途中で終了しました。')
      }
      const finalResult = streamState.finalEvent

      if (finalResult.current_plan !== undefined) {
        setPlanFromChat(finalResult.current_plan ?? '')
      }

      const remainingText = finalResult.remaining_text
      const remainingTextValue =
        typeof remainingText === 'string' && remainingText !== 'Empty' ? remainingText : null
      const finalText = remainingTextValue ?? finalResult.response ?? ''

      updateMessageMeta(loadingMessageId, {
        text: finalText,
        type: undefined,
        loading_variant: undefined,
        pending: false,
      })

      const updates: ChatMessage[] = []
      if (finalResult.yes_no_phrase) {
        updates.push({
          id: `yesno-${Date.now()}`,
          sender: 'bot',
          text: finalResult.yes_no_phrase,
          type: 'yesno',
        })
      }
      if (finalResult.choices && Array.isArray(finalResult.choices) && finalResult.choices.length > 0) {
        updates.push({
          id: `selection-${Date.now()}`,
          sender: 'bot',
          choices: finalResult.choices,
          type: 'selection',
        })
      }
      if (finalResult.is_date_select) {
        updates.push({
          id: `date-selection-${Date.now()}`,
          sender: 'bot',
          type: 'date_selection',
        })
      }
      if (updates.length > 0) {
        setMessages((prev) => [...prev, ...updates])
      }

      finishSending()
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === 'AbortError'
      const errMessage = error instanceof Error ? error.message : ''
      const message = isAbort
        ? 'サーバーからの応答がありません。もう一度お試しください。'
        : errMessage && errMessage !== 'Failed to fetch'
          ? errMessage
          : FALLBACK_ERROR_MESSAGE

      setMessages((prev) =>
        prev
          .filter((messageItem) => messageItem.id !== loadingMessageId)
          .concat({ id: `error-${Date.now()}`, sender: 'bot', text: message }),
      )
      finishSending()
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }

  const addSystemMessageFn = (text: string) => {
    setMessages((prev) => [...prev, { id: `sys-${Date.now()}`, sender: 'bot', text }])
  }

  return {
    messages,
    loading,
    planFromChat,
    sendMessage,
    addSystemMessage: addSystemMessage ? addSystemMessageFn : () => {},
  }
}
