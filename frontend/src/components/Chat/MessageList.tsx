import { useEffect, useLayoutEffect, useRef } from 'react'
import type { UIEvent } from 'react'
import MessageItem from './MessageItem'
import './Chat.css'
import type { ChatMessage } from '../../types/chat'

type MessageListProps = {
  messages: ChatMessage[]
  autoScroll: boolean
  isStreaming?: boolean
  onScroll?: (event: UIEvent<HTMLDivElement>) => void
  onYesNo: (value: string) => void
  disabled: boolean
}

const MessageList = ({
  messages,
  autoScroll,
  isStreaming = false,
  onScroll,
  onYesNo,
  disabled,
}: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)
  const autoScrollingRef = useRef(false)
  const autoScrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (autoScrollTimeoutRef.current) {
        clearTimeout(autoScrollTimeoutRef.current)
      }
    }
  }, [])

  const markAutoScrolling = () => {
    autoScrollingRef.current = true
    if (autoScrollTimeoutRef.current) {
      clearTimeout(autoScrollTimeoutRef.current)
    }
    autoScrollTimeoutRef.current = setTimeout(() => {
      autoScrollingRef.current = false
    }, 120)
  }

  const scrollToBottom = (behavior: ScrollBehavior = 'auto') => {
    if (!autoScroll || !listRef.current) return

    const target = listRef.current
    markAutoScrolling()
    if (behavior === 'smooth') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
      return
    }

    target.scrollTop = target.scrollHeight
  }

  useLayoutEffect(() => {
    scrollToBottom('auto')
  }, [messages, autoScroll])

  useEffect(() => {
    const target = listRef.current
    if (!target || typeof ResizeObserver === 'undefined') return

    let rafId: number | null = null
    const observer = new ResizeObserver(() => {
      if (!autoScroll) return
      if (rafId) cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(() => {
        scrollToBottom('auto')
      })
    })

    observer.observe(target)

    return () => {
      if (rafId) cancelAnimationFrame(rafId)
      observer.disconnect()
    }
  }, [autoScroll])

  useEffect(() => {
    if (!autoScroll || !isStreaming) return

    const intervalId = setInterval(() => {
      scrollToBottom('auto')
    }, 1500)

    return () => clearInterval(intervalId)
  }, [autoScroll, isStreaming])

  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
    if (autoScrollingRef.current) return
    if (onScroll) onScroll(event)
  }

  return (
    <div ref={listRef} className="card-body chat-messages" onScroll={handleScroll}>
      {messages.map((message, index) => (
        <MessageItem
          key={message.id}
          message={message}
          onYesNo={onYesNo}
          disabled={disabled || index !== messages.length - 1}
          isLast={index === messages.length - 1}
          scrollToBottom={scrollToBottom}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  )
}

export default MessageList
