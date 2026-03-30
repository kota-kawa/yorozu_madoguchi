/**
 * EN: Provide the useChat module implementation.
 * JP: useChat モジュールの実装を定義する。
 */
import { useState, useEffect, useRef } from 'react'
import { apiUrl } from '../utils/apiBase'
import { getStoredUserType } from '../utils/userType'
import { consumeChatSse } from '../utils/sseChatStream'
import type { ChatApiResponse, ChatStreamFinalEvent } from '../types/api'
import type { ChatMessage, ChatMessageUpdate } from '../types/chat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text: 'どんな旅行の計画を一緒に立てますか？😊',
}

/**
 * EN: Declare the useChat value.
 * JP: useChat の値を宣言する。
 */
export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage])
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState('')
  /**
   * EN: Declare the inFlightRef value.
   * JP: inFlightRef の値を宣言する。
   */
  const inFlightRef = useRef(false)

  // マウント時にリセットAPIを呼ぶ
  useEffect(() => {
    /**
     * EN: Declare the controller value.
     * JP: controller の値を宣言する。
     */
    const controller = new AbortController()
    fetch(apiUrl('/api/reset'), { method: 'POST', signal: controller.signal, credentials: 'include' }).catch(
      () => {},
    )
    return () => controller.abort()
  }, [])

  /**
   * EN: Declare the updateMessageText value.
   * JP: updateMessageText の値を宣言する。
   */
  const updateMessageText = (id: string, updater: string | ((prevText: string) => string)) => {
    setMessages((prev) =>
      prev.map((message) => {
        if (message.id !== id) return message
        /**
         * EN: Declare the nextText value.
         * JP: nextText の値を宣言する。
         */
        const nextText = typeof updater === 'function' ? updater(message.text ?? '') : updater
        return { ...message, text: nextText }
      }),
    )
  }

  /**
   * EN: Declare the updateMessageMeta value.
   * JP: updateMessageMeta の値を宣言する。
   */
  const updateMessageMeta = (id: string, updates: ChatMessageUpdate) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === id ? { ...message, ...updates } : message)),
    )
  }

  /**
   * EN: Declare the finishSending value.
   * JP: finishSending の値を宣言する。
   */
  const finishSending = () => {
    inFlightRef.current = false
    setLoading(false)
  }

  /**
   * EN: Declare the sendMessage value.
   * JP: sendMessage の値を宣言する。
   */
  const sendMessage = async (text: string) => {
    if (inFlightRef.current) return

    /**
     * EN: Declare the trimmed value.
     * JP: trimmed の値を宣言する。
     */
    const trimmed = text.trim()
    if (!trimmed) return

    if (trimmed.length > 3000) {
      alert('入力された文字数が3000文字を超えています。3000文字以内で入力してください。')
      return
    }

    inFlightRef.current = true

    /**
     * EN: Declare the userMessage value.
     * JP: userMessage の値を宣言する。
     */
    const userMessage: ChatMessage = { id: `user-${Date.now()}`, sender: 'user', text: trimmed }
    /**
     * EN: Declare the loadingMessageId value.
     * JP: loadingMessageId の値を宣言する。
     */
    const loadingMessageId = `bot-${Date.now()}`
    /**
     * EN: Declare the loadingMessage value.
     * JP: loadingMessage の値を宣言する。
     */
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
      /**
       * EN: Declare the response value.
       * JP: response の値を宣言する。
       */
      const response = await fetch(apiUrl('/travel_send_message'), {
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
      console.error("SendMessage Error:", error)
      /**
       * EN: Declare the errMessage value.
       * JP: errMessage の値を宣言する。
       */
      const errMessage = error instanceof Error ? error.message : ''
      /**
       * EN: Declare the displayMessage value.
       * JP: displayMessage の値を宣言する。
       */
      const displayMessage = errMessage && errMessage !== 'Failed to fetch' 
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
  
  /**
   * EN: Declare the addSystemMessage value.
   * JP: addSystemMessage の値を宣言する。
   */
  const addSystemMessage = (text: string) => {
      setMessages((prev) => [
        ...prev,
        { id: `sys-${Date.now()}`, sender: 'bot', text },
      ])
  }

  return {
    messages,
    loading,
    planFromChat,
    sendMessage,
    addSystemMessage
  }
}
