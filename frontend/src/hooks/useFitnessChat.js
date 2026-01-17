import { useEffect, useState } from 'react'
import { getStoredUserType } from '../utils/userType'

const initialMessage = {
  id: 'welcome',
  sender: 'bot',
  text: '目的（筋肥大・減量・健康維持など）と、今の運動頻度や使える器具を教えてください。',
}

export const useFitnessChat = () => {
  const [messages, setMessages] = useState([initialMessage])
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState('')

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
      text: '回答を考えています...',
      pending: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setLoading(true)

    try {
      const response = await fetch('/fitness_send_message', {
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

      setMessages((prev) => {
        const withoutPending = prev.filter(
          (message) => message.id !== loadingMessage.id && message.type !== 'yesno',
        )
        return [...withoutPending, ...updates]
      })

      if (data?.current_plan !== undefined) {
        setPlanFromChat(data.current_plan)
      }
    } catch (error) {
      console.error('SendMessage Error:', error)
      const displayMessage =
        error.message && error.message !== 'Failed to fetch'
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

  return {
    messages,
    loading,
    planFromChat,
    sendMessage,
  }
}
