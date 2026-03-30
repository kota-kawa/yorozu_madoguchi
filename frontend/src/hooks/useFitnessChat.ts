import { useEffect, useRef, useState } from 'react'
import { apiUrl } from '../utils/apiBase'
import { getStoredUserType } from '../utils/userType'
import { consumeChatSse } from '../utils/sseChatStream'
import type { ChatApiResponse, ChatStreamFinalEvent } from '../types/api'
import type { ChatMessage, ChatMessageUpdate } from '../types/chat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text: '目的（筋肥大・減量・健康維持など）と、今の運動頻度や使える器具を教えてください。',
}

export const useFitnessChat = () => {
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

    try {
      const response = await fetch(apiUrl('/fitness_send_message'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ message: trimmed, user_type: getStoredUserType(), stream: true }),
        credentials: 'include',
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
      let finalEvent: ChatStreamFinalEvent | null = null
      let streamUsedWebSearch = false

      updateMessageMeta(loadingMessageId, {
        text: '',
        type: 'loading',
        loading_variant: 'thinking',
        pending: false,
      })

      const flushBufferedText = () => {
        if (!bufferedText) return
        const chunkToAppend = bufferedText
        bufferedText = ''
        updateMessageText(loadingMessageId, (prevText) => `${prevText}${chunkToAppend}`)
      }

      await consumeChatSse(response, (event) => {
        if (event.type === 'meta') {
          streamUsedWebSearch = Boolean(event.used_web_search)
          updateMessageMeta(loadingMessageId, {
            loading_variant: streamUsedWebSearch ? 'web_search' : 'thinking',
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
          finalEvent = event
        }
      })

      if (flushTimeoutId) {
        clearTimeout(flushTimeoutId)
        flushTimeoutId = null
      }
      flushBufferedText()

      if (!finalEvent) {
        throw new Error('ストリーミングが途中で終了しました。')
      }

      if (finalEvent.current_plan !== undefined) {
        setPlanFromChat(finalEvent.current_plan ?? '')
      }

      const remainingText = finalEvent.remaining_text
      const remainingTextValue =
        typeof remainingText === 'string' && remainingText !== 'Empty' ? remainingText : null
      const finalText = remainingTextValue ?? finalEvent.response ?? ''

      updateMessageMeta(loadingMessageId, {
        text: finalText,
        type: undefined,
        loading_variant: undefined,
        pending: false,
      })

      const updates: ChatMessage[] = []
      if (finalEvent.yes_no_phrase) {
        updates.push({
          id: `yesno-${Date.now()}`,
          sender: 'bot',
          text: finalEvent.yes_no_phrase,
          type: 'yesno',
        })
      }
      if (finalEvent.choices && Array.isArray(finalEvent.choices) && finalEvent.choices.length > 0) {
        updates.push({
          id: `selection-${Date.now()}`,
          sender: 'bot',
          choices: finalEvent.choices,
          type: 'selection',
        })
      }
      if (finalEvent.is_date_select) {
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
      console.error('SendMessage Error:', error)
      const errMessage = error instanceof Error ? error.message : ''
      const displayMessage =
        errMessage && errMessage !== 'Failed to fetch'
          ? errMessage
          : 'サーバーからの応答に失敗しました。時間をおいて再試行してください。'

      setMessages((prev) =>
        prev
          .filter((message) => message.id !== loadingMessageId)
          .concat({
            id: `error-${Date.now()}`,
            sender: 'bot',
            text: displayMessage,
          }),
      )
      finishSending()
    }
  }

  return {
    messages,
    loading,
    planFromChat,
    sendMessage,
  }
}
