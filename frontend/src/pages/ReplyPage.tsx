import { useEffect, useState } from 'react'
import type { FormEvent, KeyboardEvent, UIEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header/Header'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { useReplyChat } from '../hooks/useReplyChat'
import { apiUrl } from '../utils/apiBase'

const SAMPLE_PROMPTS = [
  'どこに行くのがおすすめ？',
  'どんな有名スポットがある？',
  '落ち着ける場所はある？',
  'ご飯に行くならどこ？',
]

const ReplyPage = () => {
  const [input, setInput] = useState('')
  const [infoOpen, setInfoOpen] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [currentPlan, setCurrentPlan] = useState('')
  const [submittingPlan, setSubmittingPlan] = useState(false)
  const navigate = useNavigate()

  const {
    messages,
    loading: chatLoading,
    planFromChat,
    sendMessage,
  } = useReplyChat()

  useEffect(() => {
    if (planFromChat !== undefined) {
      setCurrentPlan(planFromChat)
    }
  }, [planFromChat])

  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget
    const isAtBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 10
    setAutoScroll(isAtBottom)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit(event)
    }
  }

  const handleSubmit = (
    event: FormEvent<HTMLFormElement> | KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    event.preventDefault()
    sendMessage(input)
    setInput('')
  }

  const submitPlan = async () => {
    if (!currentPlan?.trim() || submittingPlan) return

    setSubmittingPlan(true)
    try {
      const response = await fetch(apiUrl('/reply_submit_plan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: currentPlan }),
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('プランの保存に失敗しました。')
      }

      navigate('/complete')
    } catch (error) {
      console.error('Reply submit failed:', error)
      alert('プランの保存に失敗しました。')
    } finally {
      setSubmittingPlan(false)
    }
  }

  const isLoading = chatLoading || submittingPlan

  return (
    <div className="app theme-reply">
      <Header
        subtitle="返信作成アシスタント"
      />

      <div className="chat-container">
        <div className="card chat-card">
          <MessageList
            messages={messages}
            autoScroll={autoScroll}
            onScroll={handleScroll}
            onYesNo={sendMessage}
            disabled={isLoading}
          />

          <div className="card-footer chat-footer">
            <InfoPanel
              isOpen={infoOpen}
              samples={SAMPLE_PROMPTS}
              onSelect={setInput}
              onClose={() => setInfoOpen(false)}
            />

            <ChatInput
              input={input}
              onInputChange={setInput}
              onKeyDown={handleKeyDown}
              onSubmit={handleSubmit}
              onToggleInfo={() => setInfoOpen((prev) => !prev)}
              disabled={isLoading}
            />
          </div>
        </div>

        <PlanViewer
          plan={currentPlan}
          isSubmitting={submittingPlan}
          onSubmit={submitPlan}
        />
      </div>

      <LoadingSpinner visible={submittingPlan} />
    </div>
  )
}

export default ReplyPage
