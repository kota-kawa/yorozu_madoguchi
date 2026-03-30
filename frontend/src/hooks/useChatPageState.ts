import { useState } from 'react'
import type { FormEvent, KeyboardEvent, UIEvent } from 'react'

type SubmitEvent = FormEvent<HTMLFormElement> | KeyboardEvent<HTMLTextAreaElement>

type UseChatPageStateOptions = {
  isSending: boolean
  sendMessage: (text: string) => void | Promise<void>
}

export const useChatPageState = ({ isSending, sendMessage }: UseChatPageStateOptions) => {
  const [input, setInput] = useState('')
  const [infoOpen, setInfoOpen] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [activeTab, setActiveTab] = useState<'chat' | 'plan'>('chat')
  const [hasNewPlan, setHasNewPlan] = useState(false)

  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget
    const isAtBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 10
    setAutoScroll(isAtBottom)
  }

  const handleSubmit = (event: SubmitEvent) => {
    event.preventDefault()
    if (isSending) return
    if (!input.trim()) return
    sendMessage(input)
    setInput('')
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit(event)
    }
  }

  const openChatTab = () => {
    setActiveTab('chat')
  }

  const openPlanTab = () => {
    setActiveTab('plan')
    setHasNewPlan(false)
  }

  return {
    input,
    setInput,
    infoOpen,
    setInfoOpen,
    autoScroll,
    activeTab,
    setActiveTab,
    hasNewPlan,
    setHasNewPlan,
    handleScroll,
    handleKeyDown,
    handleSubmit,
    openChatTab,
    openPlanTab,
  }
}
