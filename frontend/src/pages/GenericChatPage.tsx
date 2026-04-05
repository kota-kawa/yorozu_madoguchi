import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header/Header'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import InfoPanel from '../components/UI/InfoPanel'
import ErrorToast from '../components/UI/ErrorToast'
import PlanViewer from '../components/Plan/PlanViewer'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import { useFeatureChat } from '../hooks/useFeatureChat'
import { clearAllPersistedChatStates } from '../hooks/useGenericChat'
import { usePlan } from '../hooks/usePlan'
import { useChatPageState } from '../hooks/useChatPageState'
import type { ChatPageConfig } from './chatPageConfigs'
import { apiUrl } from '../utils/apiBase'
import type { AppError, AppErrorType } from '../types/error'
import { normalizeAppError, toFrontendAppError } from '../utils/errorHandling'
import type { ApiErrorResponse } from '../types/api'

type GenericChatPageProps = {
  config: ChatPageConfig
}

const GenericChatPage = ({ config }: GenericChatPageProps) => {
  const navigate = useNavigate()
  const [toastMessage, setToastMessage] = useState('')
  const [isToastVisible, setIsToastVisible] = useState(false)
  const [startingNewSession, setStartingNewSession] = useState(false)
  const [isConfirmNewSessionOpen, setIsConfirmNewSessionOpen] = useState(false)

  const showToast = useCallback((message: string) => {
    const trimmed = message.trim()
    if (!trimmed) return
    setToastMessage(trimmed)
    setIsToastVisible(true)
  }, [])

  const hideToast = useCallback(() => {
    setIsToastVisible(false)
  }, [])

  const shouldShowSubmitErrorToast = useCallback(
    (errorType: AppErrorType): boolean => {
      const submitPlanConfig = config.submitPlan
      if (!submitPlanConfig) return false
      const filter = submitPlanConfig.toastErrorTypes
      if (!filter || filter.length === 0) return true
      return filter.includes(errorType)
    },
    [config.submitPlan],
  )

  const handleChatError = useCallback(
    (error: AppError) => {
      showToast(error.message)
    },
    [showToast],
  )

  const {
    messages,
    loading: chatLoading,
    planFromChat,
    sendMessage,
    addSystemMessage,
    resetConversation,
  } = useFeatureChat(
    config.feature,
    { onError: handleChatError },
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
    onError: (error) => {
      console.error(`${config.feature} submit failed:`, error)
      if (!shouldShowSubmitErrorToast(error.type)) return
      showToast(submitPlanConfig?.toastOnError || error.message)
    },
  })

  const isLoading = chatLoading || (hasSubmitPlan && submittingPlan)
  const isChatInputDisabled = isLoading || startingNewSession
  const isDecisionInputDisabled = startingNewSession || (hasSubmitPlan && submittingPlan)

  const {
    input,
    setInput,
    infoOpen,
    setInfoOpen,
    autoScroll,
    setAutoScroll,
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

  const handleStartNewSession = useCallback(async () => {
    if (startingNewSession || isLoading) return
    setStartingNewSession(true)
    try {
      const response = await fetch(apiUrl('/api/reset'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_session: true }),
        credentials: 'include',
      })
      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as ApiErrorResponse | null
        throw toFrontendAppError(data, response.status, '新しいセッションの作成に失敗しました。')
      }

      resetConversation()
      clearAllPersistedChatStates()
      setCurrentPlan('')
      setHasNewPlan(false)
      setInput('')
      setInfoOpen(false)
      setAutoScroll(true)
      openChatTab()
      hideToast()
      setIsConfirmNewSessionOpen(false)
    } catch (error) {
      showToast(normalizeAppError(error).message)
    } finally {
      setStartingNewSession(false)
    }
  }, [
    startingNewSession,
    isLoading,
    resetConversation,
    setCurrentPlan,
    setHasNewPlan,
    setInput,
    setInfoOpen,
    setAutoScroll,
    openChatTab,
    hideToast,
    showToast,
  ])

  const handleOpenNewSessionConfirm = useCallback(() => {
    if (startingNewSession || isLoading) return
    setIsConfirmNewSessionOpen(true)
  }, [startingNewSession, isLoading])

  const handleCloseNewSessionConfirm = useCallback(() => {
    if (startingNewSession) return
    setIsConfirmNewSessionOpen(false)
  }, [startingNewSession])

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
      <Header
        {...config.header}
      />

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
            onYesNo={(value) => {
              setAutoScroll(true)
              void sendMessage(value)
            }}
            disabled={isDecisionInputDisabled}
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
              onStartNewSession={handleOpenNewSessionConfirm}
              isStartingNewSession={startingNewSession}
              onError={handleChatError}
              disabled={isChatInputDisabled}
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
      <ErrorToast message={toastMessage} visible={isToastVisible} onClose={hideToast} />
      {isConfirmNewSessionOpen ? (
        <div
          className="session-confirm-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="新しいセッション確認"
          onClick={handleCloseNewSessionConfirm}
        >
          <div className="session-confirm-card" onClick={(event) => event.stopPropagation()}>
            <h2 className="session-confirm-title">このチャットルームを終了しますか？</h2>
            <p className="session-confirm-text">会話履歴はリセットされ、新しいセッションが開始されます。</p>
            <div className="session-confirm-actions">
              <button
                type="button"
                className="session-confirm-cancel"
                onClick={handleCloseNewSessionConfirm}
                disabled={startingNewSession}
              >
                キャンセル
              </button>
              <button
                type="button"
                className="session-confirm-submit"
                onClick={() => {
                  void handleStartNewSession()
                }}
                disabled={startingNewSession}
              >
                {startingNewSession ? '作成中...' : '終了して新規開始'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default GenericChatPage
