/**
 * EN: Provide the StudyPage module implementation.
 * JP: StudyPage モジュールの実装を定義する。
 */
import { useEffect, useState } from 'react'
import type { FormEvent, KeyboardEvent, UIEvent } from 'react'
import Header from '../components/Header/Header'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import { useStudyChat } from '../hooks/useStudyChat'

/**
 * EN: Declare the SAMPLE_PROMPTS value.
 * JP: SAMPLE_PROMPTS の値を宣言する。
 */
const SAMPLE_PROMPTS = [
  '今日の授業メモを整理ノートにして。',
  '用語集を作って。',
  '重要ポイントを短くまとめて。',
  '確認問題を作って。',
]

/**
 * EN: Declare the StudyPage value.
 * JP: StudyPage の値を宣言する。
 */
const StudyPage = () => {
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
  } = useStudyChat()

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
    if (chatLoading) return
    if (!input.trim()) return
    sendMessage(input)
    setInput('')
  }

  return (
    <div className="app theme-study">
      <Header subtitle="学習アシスタント" />

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

export default StudyPage
