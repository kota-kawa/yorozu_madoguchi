/**
 * EN: Provide the useChat module implementation.
 * JP: useChat モジュールの実装を定義する。
 */
import { useState, useEffect, useRef } from 'react'
import { apiUrl } from '../utils/apiBase'
import { getStoredUserType } from '../utils/userType'
import { streamWithWorker } from '../utils/streamHelper'
import type { ChatApiResponse } from '../types/api'
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
   * EN: Declare the workerRef value.
   * JP: workerRef の値を宣言する。
   */
  const workerRef = useRef<Worker | null>(null)
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

  useEffect(() => {
    return () => {
      workerRef.current?.terminate()
    }
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
    workerRef.current?.terminate()
    workerRef.current = null

    /**
     * EN: Declare the userMessage value.
     * JP: userMessage の値を宣言する。
     */
    const userMessage = { id: `user-${Date.now()}`, sender: 'user', text: trimmed }
    /**
     * EN: Declare the loadingMessageId value.
     * JP: loadingMessageId の値を宣言する。
     */
    const loadingMessageId = `bot-${Date.now()}`
    /**
     * EN: Declare the loadingMessage value.
     * JP: loadingMessage の値を宣言する。
     */
    const loadingMessage = {
      id: loadingMessageId,
      sender: 'bot',
      text: '考えています',
      type: 'loading',
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, user_type: getStoredUserType() }),
        credentials: 'include',
      })

      /**
       * EN: Declare the data value.
       * JP: data の値を宣言する。
       */
      const data = (await response.json().catch(() => null)) as ChatApiResponse | null

      if (!response.ok) {
        /**
         * EN: Declare the serverMessage value.
         * JP: serverMessage の値を宣言する。
         */
        const serverMessage = data?.response
        throw new Error(serverMessage || `Server Error: ${response.status}`)
      }

      if (data?.error) {
         throw new Error(data.response || 'API Error')
      }

      /**
       * EN: Declare the remainingText value.
       * JP: remainingText の値を宣言する。
       */
      const remainingText = data?.remaining_text
      /**
       * EN: Declare the remainingTextValue value.
       * JP: remainingTextValue の値を宣言する。
       */
      const remainingTextValue =
        typeof remainingText === 'string' && remainingText !== 'Empty' ? remainingText : null
      
      if (data?.current_plan !== undefined) {
        setPlanFromChat(data.current_plan ?? '')
      }

      /**
       * EN: Declare the handleExtras value.
       * JP: handleExtras の値を宣言する。
       */
      const handleExtras = () => {
        const updates: ChatMessage[] = []
        if (data?.yes_no_phrase) {
            updates.push({
            id: `yesno-${Date.now()}`,
            sender: 'bot',
            text: data.yes_no_phrase,
            type: 'yesno',
            })
        }
        if (data?.choices && Array.isArray(data.choices) && data.choices.length > 0) {
            updates.push({
            id: `selection-${Date.now()}`,
            sender: 'bot',
            choices: data.choices,
            type: 'selection',
            })
        }
        if (data?.is_date_select) {
            updates.push({
            id: `date-selection-${Date.now()}`,
            sender: 'bot',
            type: 'date_selection',
            })
        }
        if (updates.length > 0) {
            setMessages((prev) => [...prev, ...updates])
        }
      }

      if (remainingTextValue !== null) {
        updateMessageMeta(loadingMessageId, { text: '', type: undefined, pending: false })

        if (typeof Worker !== 'undefined') {
            /**
             * EN: Declare the worker value.
             * JP: worker の値を宣言する。
             */
            const worker = new Worker(
              new URL('../workers/textGeneratorWorker.ts', import.meta.url),
              { type: 'module' },
            )
            workerRef.current = worker
  
            /**
             * EN: Declare the streamFlushIntervalMs value.
             * JP: streamFlushIntervalMs の値を宣言する。
             */
            const streamFlushIntervalMs = 30
            let bufferedText = ''
            let flushTimeoutId: ReturnType<typeof setTimeout> | null = null
  
            /**
             * EN: Declare the flushBufferedText value.
             * JP: flushBufferedText の値を宣言する。
             */
            const flushBufferedText = () => {
              if (!bufferedText) return
              /**
               * EN: Declare the chunkToAppend value.
               * JP: chunkToAppend の値を宣言する。
               */
              const chunkToAppend = bufferedText
              bufferedText = ''
              updateMessageText(loadingMessageId, (prevText) => `${prevText}${chunkToAppend}`)
            }
  
            streamWithWorker(
              worker,
              remainingTextValue,
              (chunk) => {
                bufferedText += chunk
                if (!flushTimeoutId) {
                  flushTimeoutId = setTimeout(() => {
                    flushTimeoutId = null
                    flushBufferedText()
                  }, streamFlushIntervalMs)
                }
              },
              () => {
                if (flushTimeoutId) {
                  clearTimeout(flushTimeoutId)
                  flushTimeoutId = null
                }
                flushBufferedText()
                finishSending()
                workerRef.current?.terminate()
                workerRef.current = null
                handleExtras()
              },
            )
        } else {
            // Worker fallback
            updateMessageMeta(loadingMessageId, { text: remainingTextValue, type: undefined, pending: false })
            finishSending()
            handleExtras()
        }
      } else {
        /**
         * EN: Declare the botText value.
         * JP: botText の値を宣言する。
         */
        const botText = data?.response || ''
        updateMessageMeta(loadingMessageId, { text: botText, type: undefined, pending: false })
        finishSending()
        handleExtras()
      }

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
