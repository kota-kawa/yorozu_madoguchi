import { useEffect, useRef } from 'react'
import MessageItem from './MessageItem'
import './Chat.css'

const MessageList = ({ messages, autoScroll, onScroll, onYesNo, disabled }) => {
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, autoScroll])

  return (
    <div className="card-body chat-messages" onScroll={onScroll}>
      {messages.map((message) => (
        <MessageItem
          key={message.id}
          message={message}
          onYesNo={onYesNo}
          disabled={disabled}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  )
}

export default MessageList
