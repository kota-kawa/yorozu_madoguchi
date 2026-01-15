import { useEffect, useRef } from 'react'
import MessageItem from './MessageItem'
import './Chat.css'

const MessageList = ({ messages, autoScroll, onScroll, onYesNo, disabled }) => {
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, autoScroll])

  return (
    <div className="card-body chat-messages" onScroll={onScroll}>
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
