import { useState, useEffect, useRef } from 'react'
import { getStoredUserType } from '../utils/userType'
import { streamWithWorker } from '../utils/streamHelper'

const initialMessage = {
  id: 'welcome',
  sender: 'bot',
  text: 'どんな旅行の計画を一緒に立てますか？😊',
}

export const useChat = () => {
  const [messages, setMessages] = useState([initialMessage])
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState('')
  const workerRef = useRef(null)

  // マウント時にリセットAPIを呼ぶ
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
    const loadingMessageId = `bot-${Date.now()}`
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
      const response = await fetch('/travel_send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, user_type: getStoredUserType() }),
      })

      const data = await response.json().catch(() => null)

      if (!response.ok) {
        const serverMessage = data?.response
        throw new Error(serverMessage || `Server Error: ${response.status}`)
      }

      if (data.error) {
         throw new Error(data.response || 'API Error')
      }

      const remainingText = data?.remaining_text
      const hasRemainingText =
        remainingText !== null && remainingText !== undefined && remainingText !== 'Empty'
      
      if (data?.current_plan !== undefined) {
        setPlanFromChat(data.current_plan)
      }

      const handleExtras = () => {
        const updates = []
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

      if (hasRemainingText) {
        updateMessageMeta(loadingMessageId, { text: '', type: undefined, pending: false })

        if (typeof Worker !== 'undefined') {
            const worker = new Worker(
              new URL('../workers/textGeneratorWorker.js', import.meta.url),
              { type: 'module' },
            )
            workerRef.current = worker
  
            const streamFlushIntervalMs = 30
            let bufferedText = ''
            let flushTimeoutId = null
  
            const flushBufferedText = () => {
              if (!bufferedText) return
              const chunkToAppend = bufferedText
              bufferedText = ''
              updateMessageText(loadingMessageId, (prevText) => `${prevText}${chunkToAppend}`)
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
                handleExtras()
              },
            )
        } else {
            // Worker fallback
            updateMessageMeta(loadingMessageId, { text: remainingText, type: undefined, pending: false })
            setLoading(false)
            handleExtras()
        }
      } else {
        const botText = data?.response || ''
        updateMessageMeta(loadingMessageId, { text: botText, type: undefined, pending: false })
        setLoading(false)
        handleExtras()
      }

    } catch (error) {
      console.error("SendMessage Error:", error)
      const displayMessage = error.message && error.message !== 'Failed to fetch' 
        ? error.message 
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
      setLoading(false)
    } 
  }
  
  const addSystemMessage = (text) => {
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
