/**
 * EN: Provide the JobPage module implementation.
 * JP: JobPage モジュールの実装を定義する。
 */
import { useEffect, useState } from 'react'
import Header from '../components/Header/Header'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import { useJobChat } from '../hooks/useJobChat'
import { useChatPageState } from '../hooks/useChatPageState'

/**
 * EN: Declare the SAMPLE_PROMPTS value.
 * JP: SAMPLE_PROMPTS の値を宣言する。
 */
const SAMPLE_PROMPTS = [
  '自己PRを400字で作りたい。強みは継続力。',
  'ESのガクチカを添削してほしい。',
  '志望動機を業界研究ベースで作ってほしい。',
  '面接の想定質問と回答の骨子を作って。',
]

/**
 * EN: Declare the JobPage value.
 * JP: JobPage の値を宣言する。
 */
const JobPage = () => {
  const [currentPlan, setCurrentPlan] = useState('')

  const {
    messages,
    loading: chatLoading,
    planFromChat,
    sendMessage,
  } = useJobChat()

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
    isSending: chatLoading,
    sendMessage,
  })

  useEffect(() => {
    if (planFromChat !== undefined) {
      setCurrentPlan(planFromChat)
      if (planFromChat && activeTab !== 'plan') {
        setHasNewPlan(true)
      }
    }
  }, [planFromChat, activeTab, setHasNewPlan])

  return (
    <div className="app theme-job">
      <Header subtitle="就活アシスタント" />

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
