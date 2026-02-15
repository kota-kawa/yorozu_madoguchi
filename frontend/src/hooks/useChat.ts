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

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([initialMessage])
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState('')
  const workerRef = useRef<Worker | null>(null)
  const inFlightRef = useRef(false)

  // マウント時にリセットAPIを呼ぶ
  useEffect(() => {
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
      const response = await fetch(apiUrl('/travel_send_message'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed, user_type: getStoredUserType() }),
        credentials: 'include',
      })

      const data = (await response.json().catch(() => null)) as ChatApiResponse | null

      if (!response.ok) {
        const serverMessage = data?.response
        throw new Error(serverMessage || `Server Error: ${response.status}`)
      }

      if (data?.error) {
         throw new Error(data.response || 'API Error')
      }

      const remainingText = data?.remaining_text
      const remainingTextValue =
        typeof remainingText === 'string' && remainingText !== 'Empty' ? remainingText : null
      
      if (data?.current_plan !== undefined) {
        setPlanFromChat(data.current_plan ?? '')
      }

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
        const botText = data?.response || ''
        updateMessageMeta(loadingMessageId, { text: botText, type: undefined, pending: false })
        finishSending()
        handleExtras()
      }

    } catch (error) {
      console.error("SendMessage Error:", error)
      const errMessage = error instanceof Error ? error.message : ''
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
