import { useState, useRef, useEffect } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import './Chat.css'

type ChatInputProps = {
  input: string
  onInputChange: (value: string) => void
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onToggleInfo: () => void
  disabled: boolean
}

const ChatInput = ({
  input,
  onInputChange,
  onKeyDown,
  onSubmit,
  onToggleInfo,
  disabled,
}: ChatInputProps) => {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [input])

  useEffect(() => {
    const viewport = window.visualViewport
    if (!viewport) {
      document.documentElement.style.setProperty('--keyboard-offset', '0px')
      return
    }

    const updateOffset = () => {
      const offset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop)
      document.documentElement.style.setProperty('--keyboard-offset', `${offset}px`)
    }

    updateOffset()
    viewport.addEventListener('resize', updateOffset)
    viewport.addEventListener('scroll', updateOffset)

    return () => {
      viewport.removeEventListener('resize', updateOffset)
      viewport.removeEventListener('scroll', updateOffset)
      document.documentElement.style.setProperty('--keyboard-offset', '0px')
    }
  }, [])

  useEffect(() => {
    // ブラウザの音声認識APIの互換性チェック
    const SpeechRecognitionConstructor =
      window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognitionConstructor) {
      const recognition = new SpeechRecognitionConstructor()
      recognition.lang = 'ja-JP'
      recognition.continuous = false
      recognition.interimResults = false

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        // 既存の入力がある場合はスペースを空けて追記
        const newValue = input ? `${input} ${transcript}` : transcript
        onInputChange(newValue)
        setIsListening(false)
      }

      recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error)
        setIsListening(false)
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = recognition
    }
  }, [input, onInputChange])

  const handleMicClick = () => {
    if (!recognitionRef.current) {
      alert('お使いのブラウザは音声入力をサポートしていません。')
      return
    }

    if (isListening) {
      recognitionRef.current.stop()
    } else {
      recognitionRef.current.start()
      setIsListening(true)
    }
  }

  return (
    <div className="chat-input-wrapper">
      <div className="chat-input">
        <button
          type="button"
          className="btn-info original-btn"
          onClick={onToggleInfo}
          aria-label="入力例を表示"
        >
          <i className="bi bi-lightbulb" aria-hidden />
        </button>

        <form className="chat-form" onSubmit={onSubmit}>
          <button
            type="button"
            className={`btn-icon original-btn mic-btn ${isListening ? 'listening' : ''}`}
            onClick={handleMicClick}
            aria-label="音声入力"
            disabled={disabled}
          >
            <i className={`bi ${isListening ? 'bi-mic-mute-fill' : 'bi-mic-fill'}`} aria-hidden />
          </button>

          <textarea
            ref={textareaRef}
            id="message"
            name="message"
            placeholder={isListening ? 'お話しください...' : 'メッセージを入力...'}
            rows={1}
            maxLength={3000}
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={onKeyDown}
            disabled={disabled}
          />

          <button
            type="submit"
            className="btn-chat original-btn"
            disabled={disabled || !input.trim()}
            aria-label="送信"
          >
            <i className="bi bi-arrow-up-short" aria-hidden />
          </button>
        </form>
      </div>
    </div>
  )
}

export default ChatInput
