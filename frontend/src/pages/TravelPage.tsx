/**
 * EN: Provide the TravelPage module implementation.
 * JP: TravelPage モジュールの実装を定義する。
 */
import { useEffect } from 'react'
import Header from '../components/Header/Header'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import { useChat } from '../hooks/useChat'
import { usePlan } from '../hooks/usePlan'
import { useChatPageState } from '../hooks/useChatPageState'

/**
 * EN: Declare the SAMPLE_PROMPTS value.
 * JP: SAMPLE_PROMPTS の値を宣言する。
 */
const SAMPLE_PROMPTS = [
  'どこに行くのがおすすめ？',
  'どんな有名スポットがある？',
  '落ち着ける場所はある？',
  'ご飯に行くならどこ？',
]

/**
 * EN: Declare the TravelPage value.
 * JP: TravelPage の値を宣言する。
 */
const TravelPage = () => {
  const {
    messages,
    loading: chatLoading,
    planFromChat,
    sendMessage,
    addSystemMessage
  } = useChat()

  const {
    currentPlan,
    setCurrentPlan,
    submittingPlan,
    submitPlan
  } = usePlan({
    submitEndpoint: '/travel_submit_plan',
    addSystemMessage,
    fetchSummaryAfterSubmit: true,
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
    if (planFromChat) {
      setCurrentPlan(planFromChat)
      if (activeTab !== 'plan') {
        setHasNewPlan(true)
      }
    }
  }, [planFromChat, setCurrentPlan, activeTab, setHasNewPlan])

  return (
    <div className="app theme-travel">
      <Header />

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

export default TravelPage
