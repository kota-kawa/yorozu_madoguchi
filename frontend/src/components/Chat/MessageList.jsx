import { useEffect, useLayoutEffect, useRef } from 'react'
import MessageItem from './MessageItem'
import './Chat.css'

const MessageList = ({ messages, autoScroll, onScroll, onYesNo, disabled }) => {
  const messagesEndRef = useRef(null)
  const listRef = useRef(null)

  const scrollToBottom = (behavior = 'auto') => {
    if (!autoScroll || !listRef.current) return

    const target = listRef.current
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

    let rafId = null
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

  return (
    <div ref={listRef} className="card-body chat-messages" onScroll={onScroll}>
      {messages.map((message, index) => (
        <MessageItem
          key={message.id}
          message={message}
          onYesNo={onYesNo}
          disabled={disabled}
          isLast={index === messages.length - 1}
          scrollToBottom={scrollToBottom}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  )
}

export default MessageList
