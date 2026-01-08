import { useState, useEffect } from 'react'

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
      text: '回答を考えています...',
      pending: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setLoading(true)

    try {
      const response = await fetch('/travel_send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
      })

      if (!response.ok) {
        throw new Error(`Server Error: ${response.status}`)
      }

      const data = await response.json()

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
      console.error("SendMessage Error:", error)
      setMessages((prev) =>
        prev
          .filter((message) => message.id !== loadingMessage.id)
          .concat({
            id: `error-${Date.now()}`,
            sender: 'bot',
            text: 'サーバーからの応答に失敗しました。時間をおいて再試行してください。',
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
