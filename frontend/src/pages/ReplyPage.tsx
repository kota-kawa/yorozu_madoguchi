/**
 * EN: Provide the ReplyPage module implementation.
 * JP: ReplyPage モジュールの実装を定義する。
 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header/Header'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { useReplyChat } from '../hooks/useReplyChat'
import { usePlan } from '../hooks/usePlan'
import { useChatPageState } from '../hooks/useChatPageState'

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
  const navigate = useNavigate()

  const {
    messages,
    loading: chatLoading,
    planFromChat,
    sendMessage,
  } = useReplyChat()

  const {
    currentPlan,
    setCurrentPlan,
    submittingPlan,
    submitPlan,
  } = usePlan({
    submitEndpoint: '/reply_submit_plan',
    onSuccess: () => navigate('/complete'),
    onError: (error) => {
      console.error('Reply submit failed:', error)
      alert('プランの保存に失敗しました。')
    },
  })

  const isLoading = chatLoading || submittingPlan

  const {
    input,
    setInput,
    infoOpen,
    setInfoOpen,
    autoScroll,
    activeTab,
    hasNewPlan,
    setHasNewPlan,
    handleScroll,
    handleKeyDown,
    handleSubmit,
    openChatTab,
    openPlanTab,
  } = useChatPageState({
    isSending: isLoading,
    sendMessage,
  })

  useEffect(() => {
    if (planFromChat !== undefined) {
      setCurrentPlan(planFromChat)
      if (planFromChat && activeTab !== 'plan') {
        setHasNewPlan(true)
      }
    }
  }, [planFromChat, activeTab, setCurrentPlan, setHasNewPlan])

  return (
    <div className="app theme-reply">
      <Header
        subtitle="返信作成アシスタント"
      />

      <div className="mobile-tab-nav">
        <button
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={openChatTab}
        >
          チャット
        </button>
        <button
          className={`tab-btn ${activeTab === 'plan' ? 'active' : ''}`}
          onClick={openPlanTab}
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
