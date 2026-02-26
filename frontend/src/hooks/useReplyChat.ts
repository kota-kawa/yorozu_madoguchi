/**
 * EN: Provide the useReplyChat module implementation.
 * JP: useReplyChat モジュールの実装を定義する。
 */
import { useEffect, useRef, useState } from 'react'
import { apiUrl } from '../utils/apiBase'
import { getStoredUserType } from '../utils/userType'
import { streamWithWorker } from '../utils/streamHelper'
import type { ChatApiResponse } from '../types/api'
import type { ChatMessage, ChatMessageUpdate } from '../types/chat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text: '返信したいLINEやDMの内容と、どのようなことをしたいか・言いたいかを教えてください。\nより多くの会話履歴が示されると良い答えを考えやすいです！',
}

/**
 * EN: Declare the useReplyChat value.
 * JP: useReplyChat の値を宣言する。
 */
export const useReplyChat = () => {
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
    const userMessage: ChatMessage = { id: `user-${Date.now()}`, sender: 'user', text: trimmed }
    /**
     * EN: Declare the botMessageId value.
     * JP: botMessageId の値を宣言する。
     */
    const botMessageId = `bot-${Date.now()}`
    /**
     * EN: Declare the botMessage value.
     * JP: botMessage の値を宣言する。
     */
    const botMessage: ChatMessage = {
      id: botMessageId,
      sender: 'bot',
      text: '考えています',
      type: 'loading',
      pending: true,
    }

    setMessages((prev) => [...prev, userMessage, botMessage])
    setLoading(true)

    /**
     * EN: Declare the controller value.
     * JP: controller の値を宣言する。
     */
    const controller = new AbortController()
    /**
     * EN: Declare the timeoutId value.
     * JP: timeoutId の値を宣言する。
     */
    const timeoutId = setTimeout(() => controller.abort(), 60000)

    try {
      /**
       * EN: Declare the response value.
       * JP: response の値を宣言する。
       */
      const response = await fetch(apiUrl('/reply_send_message'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, user_type: getStoredUserType() }),
        credentials: 'include',
        signal: controller.signal,
      })

      /**
       * EN: Declare the data value.
       * JP: data の値を宣言する。
       */
      const data = (await response.json().catch(() => null)) as ChatApiResponse | null

      if (!response.ok) {
        throw new Error(data?.error || data?.response || `Server Error: ${response.status}`)
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
        updateMessageMeta(botMessageId, { text: '', type: undefined, pending: false })

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
            updateMessageText(botMessageId, (prevText) => `${prevText}${chunkToAppend}`)
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
          updateMessageMeta(botMessageId, { text: remainingTextValue, type: undefined, pending: false })
          finishSending()
          handleExtras()
        }
      } else {
        /**
         * EN: Declare the fallbackText value.
         * JP: fallbackText の値を宣言する。
         */
        const fallbackText = data?.response || ''
        setMessages((prev) =>
          prev.map((message) =>
            message.id === botMessageId
              ? {
                  ...message,
                  text: fallbackText,
                  type: undefined,
                  pending: false,
                }
              : message,
          ),
        )
        finishSending()
        handleExtras()
      }
    } catch (error) {
      /**
       * EN: Declare the isAbort value.
       * JP: isAbort の値を宣言する。
       */
      const isAbort = error instanceof DOMException && error.name === 'AbortError'
      /**
       * EN: Declare the fallbackMessage value.
       * JP: fallbackMessage の値を宣言する。
       */
      const fallbackMessage =
        error instanceof Error ? error.message : 'サーバーからの応答に失敗しました。'
      /**
       * EN: Declare the message value.
       * JP: message の値を宣言する。
       */
      const message = isAbort
        ? 'サーバーからの応答がありません。もう一度お試しください。'
        : fallbackMessage

      setMessages((prev) =>
        prev
          .filter((messageItem) => messageItem.id !== botMessageId)
          .concat({ id: `error-${Date.now()}`, sender: 'bot', text: message }),
      )
      finishSending()
    } finally {
      clearTimeout(timeoutId)
    }
  }

  return {
    messages,
    loading,
    planFromChat,
    sendMessage,
  }
}
