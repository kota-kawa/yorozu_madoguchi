import { useEffect, useRef, useState } from 'react'
import { getStoredUserType } from '../utils/userType'

const initialMessage = {
  id: 'welcome',
  sender: 'bot',
  text: '返信したいLINEやDMの内容と、どのようなことをしたいか・言いたいかを教えてください。\nより多くの会話履歴が示されると良い答えを考えやすいです！',
}

const streamWithWorker = (worker, text, onChunk, onDone) => {
  worker.onmessage = (event) => {
    if (event.data?.type === 'text') {
      onChunk(event.data.content)
      return
    }

    if (event.data?.type === 'done') {
      onDone()
    }
  }
  worker.postMessage({ remaining_text: text })
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
      text: '回答を考えています...',
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
        updateMessageText(botMessageId, '')

        if (typeof Worker !== 'undefined') {
          const worker = new Worker(
            new URL('../workers/textGeneratorWorker.js', import.meta.url),
            { type: 'module' },
          )
          workerRef.current = worker

          streamWithWorker(
            worker,
            remainingText,
            (chunk) => updateMessageText(botMessageId, (prevText) => `${prevText}${chunk}`),
            () => {
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
          updateMessageText(botMessageId, remainingText)
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
