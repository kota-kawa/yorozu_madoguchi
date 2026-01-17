import { useState, useEffect } from 'react'
import { getStoredUserType } from '../utils/userType'

const initialMessage = {
  id: 'welcome',
  sender: 'bot',
  text: 'どんな旅行の計画を一緒に立てますか？😊',
}

export const useChat = () => {
  const [messages, setMessages] = useState([initialMessage])
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState('')

  // マウント時にリセットAPIを呼ぶ
  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/reset', { method: 'POST', signal: controller.signal }).catch(() => {})
    return () => controller.abort()
  }, [])

  const sendMessage = async (text) => {
    const trimmed = text.trim()
    if (!trimmed) return

    if (trimmed.length > 3000) {
      alert('入力された文字数が3000文字を超えています。3000文字以内で入力してください。')
      return
    }

    const userMessage = { id: `user-${Date.now()}`, sender: 'user', text: trimmed }
    const loadingMessage = {
      id: `loading-${Date.now()}`,
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
      const botText = hasRemainingText ? remainingText : data?.response

      const updates = []
      if (botText) {
        updates.push({ id: `bot-${Date.now()}`, sender: 'bot', text: botText })
      }
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

      setMessages((prev) => {
        const withoutPending = prev.filter(
          (message) => 
            message.id !== loadingMessage.id && 
            message.type !== 'yesno' && 
            message.type !== 'selection' &&
            message.type !== 'date_selection',
        )
        return [...withoutPending, ...updates]
      })

      if (data?.current_plan !== undefined) {
        setPlanFromChat(data.current_plan)
      }
    } catch (error) {
      console.error("SendMessage Error:", error)
      const displayMessage = error.message && error.message !== 'Failed to fetch' 
        ? error.message 
        : 'サーバーからの応答に失敗しました。時間をおいて再試行してください。'

      setMessages((prev) =>
        prev
          .filter((message) => message.id !== loadingMessage.id)
          .concat({
            id: `error-${Date.now()}`,
            sender: 'bot',
            text: displayMessage,
          }),
      )
    } finally {
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
