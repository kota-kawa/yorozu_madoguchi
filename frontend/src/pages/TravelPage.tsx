import { useEffect, useState } from 'react'
import type { FormEvent, KeyboardEvent, UIEvent } from 'react'
import Header from '../components/Header/Header'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import { useChat } from '../hooks/useChat'
import { usePlan } from '../hooks/usePlan'

const SAMPLE_PROMPTS = [
  'どこに行くのがおすすめ？',
  'どんな有名スポットがある？',
  '落ち着ける場所はある？',
  'ご飯に行くならどこ？',
]

const TravelPage = () => {
  const [input, setInput] = useState('')
  const [infoOpen, setInfoOpen] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [activeTab, setActiveTab] = useState<'chat' | 'plan'>('chat')
  const [hasNewPlan, setHasNewPlan] = useState(false)

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
  } = usePlan(addSystemMessage)

  useEffect(() => {
    if (planFromChat) {
      setCurrentPlan(planFromChat)
      if (activeTab !== 'plan') {
        setHasNewPlan(true)
      }
    }
  }, [planFromChat, setCurrentPlan, activeTab])

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

  const isLoading = chatLoading || submittingPlan

  return (
    <div className="app theme-travel">
      <Header />

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
            onScroll={handleScroll}
            onYesNo={sendMessage}
            disabled={isLoading}
          />

          <div className="card-footer">
            <InfoPanel
              isOpen={infoOpen}
              samples={SAMPLE_PROMPTS}
              onSelect={setInput}
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
