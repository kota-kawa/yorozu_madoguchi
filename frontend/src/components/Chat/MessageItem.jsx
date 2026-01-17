import { useState, useEffect, useRef, memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './Chat.css'

const MessageItem = memo(({ message, onYesNo, disabled, isLast, scrollToBottom }) => {
  const [displayedText, setDisplayedText] = useState('')
  const dateRef = useRef(null)

  const scrollRafRef = useRef(null)

  useEffect(() => {
    if (!isLast || !scrollToBottom) return

    if (scrollRafRef.current) {
      cancelAnimationFrame(scrollRafRef.current)
    }

    scrollRafRef.current = requestAnimationFrame(() => {
      scrollToBottom('auto')
    })

    return () => {
      if (scrollRafRef.current) {
        cancelAnimationFrame(scrollRafRef.current)
        scrollRafRef.current = null
      }
    }
  }, [displayedText, isLast, scrollToBottom])

  useEffect(() => {
    if (message.sender === 'user' || !message.text || message.type === 'loading') {
      setDisplayedText(message.text)
      return
    }

    // すでに表示済みならアニメーションしない（簡易判定: テキストが同じなら即時セットもありだが、
    // memo化されているのでマウント時のみ走ることを期待）
    setDisplayedText('')
    
    let currentIndex = 0
    const text = message.text
    const intervalId = setInterval(() => {
      setDisplayedText((prev) => {
        if (currentIndex >= text.length) {
          clearInterval(intervalId)
          return text
        }
        const nextChar = text[currentIndex]
        currentIndex++
        return prev + nextChar
      })
    }, 20)

    return () => clearInterval(intervalId)
  }, [message.text, message.sender])

  const handleDateSubmit = () => {
    if (dateRef.current && dateRef.current.value) {
      const date = dateRef.current.value
      const [year, month, day] = date.split('-')
      const formattedDate = `${year}年${parseInt(month)}月${parseInt(day)}日`
      onYesNo(formattedDate)
    }
  }

  if (message.type === 'loading') {
    return (
      <div className={`chat-message ${message.sender} loading-message`} aria-live="polite">
        <div className="loading-content">
          <span className="loading-stars" aria-hidden="true">
            <span className="loading-star star-main" />
            <span className="loading-star star-secondary" />
          </span>
          <span className="loading-text">{message.text}</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`chat-message ${message.sender}`}>
      <div className="markdown-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {displayedText}
        </ReactMarkdown>
      </div>
      {/* 完了後にボタンを表示するために、テキスト表示完了を待つロジックを入れることもできるが
          今回はシンプルに常時表示（テキストと同時に出る形でも違和感は少ない） */}
      {message.type === 'yesno' && (
        <>
          <div className="button-container">
            <button
              type="button"
              className="btn btn-yes"
              onClick={() => onYesNo('はい')}
              disabled={disabled}
            >
              はい<i className="bi bi-hand-thumbs-up-fill" aria-hidden />
            </button>
            <button
              type="button"
              className="btn btn-no"
              onClick={() => onYesNo('いいえ')}
              disabled={disabled}
            >
              いいえ <i className="bi bi-hand-thumbs-down-fill" aria-hidden />
            </button>
          </div>
          <small className="selection-note">※他に要望があれば通常のチャットに入力できます</small>
        </>
      )}
      {message.type === 'selection' && (
        <>
          <div className="button-container selection-container">
            {message.choices.map((choice, index) => (
              <button
                key={index}
                type="button"
                className="btn btn-option"
                onClick={() => onYesNo(choice)}
                disabled={disabled}
              >
                {choice}
              </button>
            ))}
          </div>
          <small className="selection-note">※他に要望があれば通常のチャットに入力できます</small>
        </>
      )}
      {message.type === 'date_selection' && (
        <div className="button-container date-input-container">
           <input type="date" ref={dateRef} className="date-input" disabled={disabled} />
           <button 
             type="button" 
             className="btn btn-option" 
             onClick={handleDateSubmit}
             disabled={disabled}
           >
             決定 <i className="bi bi-send-fill" aria-hidden />
           </button>
        </div>
      )}
    </div>
  )
})

export default MessageItem
