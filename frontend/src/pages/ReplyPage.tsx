/**
 * EN: Provide the ReplyPage module implementation.
 * JP: ReplyPage モジュールの実装を定義する。
 */
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

/**
 * EN: Declare the SAMPLE_PROMPTS value.
 * JP: SAMPLE_PROMPTS の値を宣言する。
 */
const SAMPLE_PROMPTS = [
  '相手:「火曜14時どうですか？」\n意図: 木曜16時を提案\n条件: 丁寧、80文字以内',
  '相手:「今月の飲み会来られる？」\n意図: 今回は不参加、次回は参加したい\n条件: カジュアルで角が立たない',
  '相手:「資料まだですか？」\n意図: 遅れを謝り、20時までに送る\n条件: 誠実で簡潔',
  '相手:「先日はありがとうございました！」\n意図: お礼を返して来週の日程相談\n条件: 丁寧で前向き、120文字以内',
]

/**
 * EN: Declare the ReplyPage value.
 * JP: ReplyPage の値を宣言する。
 */
const ReplyPage = () => {
  const [input, setInput] = useState('')
  const [infoOpen, setInfoOpen] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [currentPlan, setCurrentPlan] = useState('')
  const [submittingPlan, setSubmittingPlan] = useState(false)
  const [activeTab, setActiveTab] = useState<'chat' | 'plan'>('chat')
  const [hasNewPlan, setHasNewPlan] = useState(false)
  /**
   * EN: Declare the navigate value.
   * JP: navigate の値を宣言する。
   */
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
      if (planFromChat && activeTab !== 'plan') {
        setHasNewPlan(true)
      }
    }
  }, [planFromChat, activeTab])

  /**
   * EN: Declare the handleScroll value.
   * JP: handleScroll の値を宣言する。
   */
  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
    /**
     * EN: Declare the target value.
     * JP: target の値を宣言する。
     */
    const target = event.currentTarget
    /**
     * EN: Declare the isAtBottom value.
     * JP: isAtBottom の値を宣言する。
     */
    const isAtBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 10
    setAutoScroll(isAtBottom)
  }

  /**
   * EN: Declare the handleKeyDown value.
   * JP: handleKeyDown の値を宣言する。
   */
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit(event)
    }
  }

  /**
   * EN: Declare the handleSubmit value.
   * JP: handleSubmit の値を宣言する。
   */
  const handleSubmit = (
    event: FormEvent<HTMLFormElement> | KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    event.preventDefault()
    if (chatLoading || submittingPlan) return
    if (!input.trim()) return
    sendMessage(input)
    setInput('')
  }

  /**
   * EN: Declare the submitPlan value.
   * JP: submitPlan の値を宣言する。
   */
  const submitPlan = async () => {
    if (!currentPlan?.trim() || submittingPlan) return

    setSubmittingPlan(true)
    try {
      /**
       * EN: Declare the response value.
       * JP: response の値を宣言する。
       */
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

  /**
   * EN: Declare the isLoading value.
   * JP: isLoading の値を宣言する。
   */
  const isLoading = chatLoading || submittingPlan

  return (
    <div className="app theme-reply">
      <Header
        subtitle="返信作成アシスタント"
      />

      <div className="mobile-tab-nav">
        <button
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          チャット
        </button>
        <button
          className={`tab-btn ${activeTab === 'plan' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('plan')
            setHasNewPlan(false)
          }}
        >
          決定内容
          {hasNewPlan && <span className="notification-dot" />}
        </button>
      </div>

      <div className="chat-container">
        <div className={`card chat-card ${activeTab === 'plan' ? 'mobile-hidden' : ''}`}>
          <MessageList
            messages={messages}
            autoScroll={autoScroll}
            isStreaming={chatLoading}
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
          className={activeTab === 'chat' ? 'mobile-hidden' : ''}
        />
      </div>

      <LoadingSpinner visible={submittingPlan} />
    </div>
  )
}

export default ReplyPage
