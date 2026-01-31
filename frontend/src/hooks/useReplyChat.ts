import { useEffect, useRef, useState } from 'react'
import { getStoredUserType } from '../utils/userType'
import { streamWithWorker } from '../utils/streamHelper'
import type { ChatApiResponse } from '../types/api'
import type { ChatMessage, ChatMessageUpdate } from '../types/chat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text: '返信したいLINEやDMの内容と、どのようなことをしたいか・言いたいかを教えてください。\nより多くの会話履歴が示されると良い答えを考えやすいです！',
}

export const useReplyChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage])
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState('')
  const workerRef = useRef<Worker | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/reset', { method: 'POST', signal: controller.signal }).catch(() => {})
    return () => controller.abort()
  }, [])

  useEffect(() => {
    return () => {
      workerRef.current?.terminate()
    }
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

  const sendMessage = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return

    if (trimmed.length > 3000) {
      alert('入力された文字数が3000文字を超えています。3000文字以内で入力してください。')
      return
    }

    workerRef.current?.terminate()
    workerRef.current = null

    const userMessage = { id: `user-${Date.now()}`, sender: 'user', text: trimmed }
    const botMessageId = `bot-${Date.now()}`
    const botMessage = {
      id: botMessageId,
      sender: 'bot',
      text: '考えています',
      type: 'loading',
      pending: true,
    }

    setMessages((prev) => [...prev, userMessage, botMessage])
    setLoading(true)

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000)

    try {
      const response = await fetch('/reply_send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, user_type: getStoredUserType() }),
        signal: controller.signal,
      })

      const data = (await response.json().catch(() => null)) as ChatApiResponse | null

      if (!response.ok) {
        throw new Error(data?.error || data?.response || `Server Error: ${response.status}`)
      }

      const remainingText = data?.remaining_text
      const yesNoPhrase = data?.yes_no_phrase
      const remainingTextValue =
        typeof remainingText === 'string' && remainingText !== 'Empty' ? remainingText : null

      if (data?.current_plan !== undefined) {
        setPlanFromChat(data.current_plan ?? '')
      }

      if (remainingTextValue !== null) {
        updateMessageMeta(botMessageId, { text: '', type: undefined, pending: false })

        if (typeof Worker !== 'undefined') {
          const worker = new Worker(
            new URL('../workers/textGeneratorWorker.ts', import.meta.url),
            { type: 'module' },
          )
          workerRef.current = worker

          const streamFlushIntervalMs = 30
          let bufferedText = ''
          let flushTimeoutId: ReturnType<typeof setTimeout> | null = null

          const flushBufferedText = () => {
            if (!bufferedText) return
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
              setLoading(false)
              workerRef.current?.terminate()
              workerRef.current = null

              if (yesNoPhrase) {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: `yesno-${Date.now()}`,
                    sender: 'bot',
                    text: yesNoPhrase,
                    type: 'yesno',
                  },
                ])
              }
            },
          )
        } else {
          updateMessageMeta(botMessageId, { text: remainingTextValue, type: undefined, pending: false })
          setLoading(false)
          if (yesNoPhrase) {
            setMessages((prev) => [
              ...prev,
              {
                id: `yesno-${Date.now()}`,
                sender: 'bot',
                text: yesNoPhrase,
                type: 'yesno',
              },
            ])
          }
        }
      } else {
        const fallbackText = yesNoPhrase || data?.response || '返信候補を準備できませんでした。'
        setMessages((prev) =>
          prev.map((message) =>
            message.id === botMessageId
              ? {
                  ...message,
                  text: fallbackText,
                  type: yesNoPhrase ? 'yesno' : undefined,
                  pending: false,
                }
              : message,
          ),
        )
        setLoading(false)
      }
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === 'AbortError'
      const fallbackMessage =
        error instanceof Error ? error.message : 'サーバーからの応答に失敗しました。'
      const message = isAbort
        ? 'サーバーからの応答がありません。もう一度お試しください。'
        : fallbackMessage

      setMessages((prev) =>
        prev
          .filter((messageItem) => messageItem.id !== botMessageId)
          .concat({ id: `error-${Date.now()}`, sender: 'bot', text: message }),
      )
      setLoading(false)
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
