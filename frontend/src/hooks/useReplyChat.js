import { useEffect, useRef, useState } from 'react'
import { getStoredUserType } from '../utils/userType'
import { streamWithWorker } from '../utils/streamHelper'

const initialMessage = {
  id: 'welcome',
  sender: 'bot',
  text: '返信したいLINEやDMの内容と、どのようなことをしたいか・言いたいかを教えてください。\nより多くの会話履歴が示されると良い答えを考えやすいです！',
}

export const useReplyChat = () => {
  const [messages, setMessages] = useState([initialMessage])
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState('')
  const workerRef = useRef(null)

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

  const updateMessageText = (id, updater) => {
    setMessages((prev) =>
      prev.map((message) => {
        if (message.id !== id) return message
        const nextText = typeof updater === 'function' ? updater(message.text) : updater
        return { ...message, text: nextText }
      }),
    )
  }

  const updateMessageMeta = (id, updates) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === id ? { ...message, ...updates } : message)),
    )
  }

  const sendMessage = async (text) => {
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

      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(data?.error || data?.response || `Server Error: ${response.status}`)
      }

      const remainingText = data?.remaining_text
      const yesNoPhrase = data?.yes_no_phrase
      const hasRemainingText =
        remainingText !== null && remainingText !== undefined && remainingText !== 'Empty'

      if (data?.current_plan !== undefined) {
        setPlanFromChat(data.current_plan)
      }

      if (hasRemainingText) {
        updateMessageMeta(botMessageId, { text: '', type: undefined, pending: false })

        if (typeof Worker !== 'undefined') {
          const worker = new Worker(
            new URL('../workers/textGeneratorWorker.js', import.meta.url),
            { type: 'module' },
          )
                      workerRef.current = worker
            
                      const streamFlushIntervalMs = 30
                      let bufferedText = ''
                      let flushTimeoutId = null
            
                      const flushBufferedText = () => {            if (!bufferedText) return
            const chunkToAppend = bufferedText
            bufferedText = ''
            updateMessageText(botMessageId, (prevText) => `${prevText}${chunkToAppend}`)
          }

          streamWithWorker(
            worker,
            remainingText,
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
          updateMessageMeta(botMessageId, { text: remainingText, type: undefined, pending: false })
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
      const message =
        error.name === 'AbortError'
          ? 'サーバーからの応答がありません。もう一度お試しください。'
          : error.message || 'サーバーからの応答に失敗しました。'

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
