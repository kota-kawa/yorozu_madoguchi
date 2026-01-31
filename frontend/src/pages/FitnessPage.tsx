import { useEffect, useState } from 'react'
import type { FormEvent, KeyboardEvent, UIEvent } from 'react'
import Header from '../components/Header/Header'
import InfoPanel from '../components/UI/InfoPanel'
import PlanViewer from '../components/Plan/PlanViewer'
import MessageList from '../components/Chat/MessageList'
import ChatInput from '../components/Chat/ChatInput'
import { useFitnessChat } from '../hooks/useFitnessChat'

const SAMPLE_PROMPTS = [
  '筋肥大したい。週3回でどんなメニューが良い？',
  '運動初心者。まず何から始めればいい？',
  '肩こり改善のための簡単な運動は？',
  '自宅でできる減量メニューを教えて',
]

const FitnessPage = () => {
  const [input, setInput] = useState('')
  const [infoOpen, setInfoOpen] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [currentPlan, setCurrentPlan] = useState('')

  const {
    messages,
    loading: chatLoading,
    planFromChat,
    sendMessage,
  } = useFitnessChat()

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

  return (
    <div className="app theme-fitness">
      <Header
        subtitle="筋トレ・フィットネスアシスタント"
      />

      <div className="chat-container">
        <div className="card chat-card">
          <MessageList
            messages={messages}
            autoScroll={autoScroll}
            onScroll={handleScroll}
            onYesNo={sendMessage}
            disabled={chatLoading}
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
              disabled={chatLoading}
            />
          </div>
        </div>

        <PlanViewer
          plan={currentPlan}
          showSubmit={false}
        />
      </div>
    </div>
  )
}

export default FitnessPage
