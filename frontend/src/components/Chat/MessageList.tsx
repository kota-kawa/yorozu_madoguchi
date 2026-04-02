/**
 * EN: Provide the MessageList module implementation.
 * JP: MessageList モジュールの実装を定義する。
 */
import { useCallback, useEffect, useLayoutEffect, useRef } from 'react'
import type { UIEvent } from 'react'
import MessageItem from './MessageItem'
import './Chat.css'
import type { ChatMessage } from '../../types/chat'

/**
 * EN: Define the MessageListProps type alias.
 * JP: MessageListProps 型エイリアスを定義する。
 */
type MessageListProps = {
  messages: ChatMessage[]
  autoScroll: boolean
  isStreaming?: boolean
  onScroll?: (event: UIEvent<HTMLDivElement>) => void
  onYesNo: (value: string) => void
  disabled: boolean
}

/**
 * EN: Declare the MessageList value.
 * JP: MessageList の値を宣言する。
 */
const MessageList = ({
  messages,
  autoScroll,
  isStreaming = false,
  onScroll,
  onYesNo,
  disabled,
}: MessageListProps) => {
  /**
   * EN: Declare the messagesEndRef value.
   * JP: messagesEndRef の値を宣言する。
   */
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  /**
   * EN: Declare the listRef value.
   * JP: listRef の値を宣言する。
   */
  const listRef = useRef<HTMLDivElement | null>(null)
  /**
   * EN: Declare the scrollToBottom value.
   * JP: scrollToBottom の値を宣言する。
   */
  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = 'auto') => {
      if (!autoScroll || !listRef.current) return

      /**
       * EN: Declare the target value.
       * JP: target の値を宣言する。
       */
      const target = listRef.current
      if (behavior === 'smooth') {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
        return
      }

      target.scrollTop = target.scrollHeight
    },
    [autoScroll],
  )

  useLayoutEffect(() => {
    scrollToBottom('auto')
  }, [messages, scrollToBottom])

  useEffect(() => {
    /**
     * EN: Declare the target value.
     * JP: target の値を宣言する。
     */
    const target = listRef.current
    if (!target || typeof ResizeObserver === 'undefined') return

    let rafId: number | null = null
    /**
     * EN: Declare the observer value.
     * JP: observer の値を宣言する。
     */
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
  }, [autoScroll, scrollToBottom])

  useEffect(() => {
    if (!autoScroll || !isStreaming) return
    scrollToBottom('auto')
  }, [autoScroll, isStreaming, scrollToBottom])

  /**
   * EN: Declare the handleScroll value.
   * JP: handleScroll の値を宣言する。
   */
  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
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
