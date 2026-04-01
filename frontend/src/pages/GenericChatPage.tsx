import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header/Header'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import { useFeatureChat } from '../hooks/useFeatureChat'
import { usePlan } from '../hooks/usePlan'
import { useChatPageState } from '../hooks/useChatPageState'
import type { ChatPageConfig } from './chatPageConfigs'

type GenericChatPageProps = {
  config: ChatPageConfig
}

const GenericChatPage = ({ config }: GenericChatPageProps) => {
  const navigate = useNavigate()
  const { messages, loading: chatLoading, planFromChat, sendMessage, addSystemMessage } = useFeatureChat(
    config.feature,
  )

  const submitPlanConfig = config.submitPlan
  const hasSubmitPlan = Boolean(submitPlanConfig)
  const {
    currentPlan,
    setCurrentPlan,
    submittingPlan,
    submitPlan,
  } = usePlan({
    submitEndpoint: submitPlanConfig?.submitEndpoint ?? '/travel_submit_plan',
    addSystemMessage: submitPlanConfig?.addSystemMessageOnSubmit ? addSystemMessage : undefined,
    fetchSummaryAfterSubmit: Boolean(submitPlanConfig?.fetchSummaryAfterSubmit),
    onSuccess: submitPlanConfig?.navigateToCompleteOnSuccess ? () => navigate('/complete') : undefined,
    onError: submitPlanConfig?.alertOnError
      ? (error) => {
          console.error(`${config.feature} submit failed:`, error)
          alert(submitPlanConfig.alertOnError)
        }
      : undefined,
  })

  const isLoading = chatLoading || (hasSubmitPlan && submittingPlan)

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
    if (planFromChat === undefined) return
    if (config.planSyncMode === 'truthy' && !planFromChat) return

    setCurrentPlan(planFromChat)
    if (planFromChat && activeTab !== 'plan') {
      setHasNewPlan(true)
    }
  }, [planFromChat, activeTab, setCurrentPlan, setHasNewPlan, config.planSyncMode])

  return (
    <div className={`app ${config.themeClassName}`}>
      <Header {...config.header} />

      <div className="mobile-tab-nav">
        <button className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`} onClick={openChatTab}>
          チャット
        </button>
        <button className={`tab-btn ${activeTab === 'plan' ? 'active' : ''}`} onClick={openPlanTab}>
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
              samples={config.samplePrompts}
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

        {hasSubmitPlan ? (
          <PlanViewer
            plan={currentPlan}
            isSubmitting={submittingPlan}
            onSubmit={submitPlan}
            className={activeTab === 'chat' ? 'mobile-hidden' : ''}
          />
        ) : (
          <PlanViewer
            plan={currentPlan}
            showSubmit={false}
            className={activeTab === 'chat' ? 'mobile-hidden' : ''}
          />
        )}
      </div>

      {hasSubmitPlan ? <LoadingSpinner visible={submittingPlan} /> : null}
    </div>
  )
}

export default GenericChatPage
