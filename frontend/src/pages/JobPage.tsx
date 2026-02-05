import { useEffect, useState } from 'react'
import type { FormEvent, KeyboardEvent, UIEvent } from 'react'
import Header from '../components/Header/Header'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import { useJobChat } from '../hooks/useJobChat'

const SAMPLE_PROMPTS = [
  '自己PRを400字で作りたい。強みは継続力。',
  'ESのガクチカを添削してほしい。',
  '志望動機を業界研究ベースで作ってほしい。',
  '面接の想定質問と回答の骨子を作って。',
]

const JobPage = () => {
  const [input, setInput] = useState('')
  const [infoOpen, setInfoOpen] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [currentPlan, setCurrentPlan] = useState('')
  const [activeTab, setActiveTab] = useState<'chat' | 'plan'>('chat')
  const [hasNewPlan, setHasNewPlan] = useState(false)

  const {
    messages,
    loading: chatLoading,
    planFromChat,
    sendMessage,
  } = useJobChat()

  useEffect(() => {
    if (planFromChat !== undefined) {
      setCurrentPlan(planFromChat)
      if (planFromChat && activeTab !== 'plan') {
        setHasNewPlan(true)
      }
    }
  }, [planFromChat, activeTab])

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

  return (
    <div className="app theme-job">
      <Header subtitle="就活アシスタント" />

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
            disabled={chatLoading}
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
              disabled={chatLoading}
            />
          </div>
        </div>

        <PlanViewer
          plan={currentPlan}
          showSubmit={false}
          className={activeTab === 'chat' ? 'mobile-hidden' : ''}
        />
      </div>
    </div>
  )
}

export default JobPage
