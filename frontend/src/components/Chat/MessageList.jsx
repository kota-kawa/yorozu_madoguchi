import { useEffect, useLayoutEffect, useRef } from 'react'
import MessageItem from './MessageItem'
import './Chat.css'

const MessageList = ({ messages, autoScroll, onScroll, onYesNo, disabled }) => {
  const messagesEndRef = useRef(null)
  const listRef = useRef(null)
  const autoScrollingRef = useRef(false)
  const autoScrollTimeoutRef = useRef(null)

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

  const scrollToBottom = (behavior = 'auto') => {
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

  const handleScroll = (event) => {
    if (autoScrollingRef.current && event.isTrusted === false) return
    if (onScroll) onScroll(event)
  }

  return (
    <div ref={listRef} className="card-body chat-messages" onScroll={handleScroll}>
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
