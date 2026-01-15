import { useState, useRef, useEffect } from 'react'
import './Chat.css'

const ChatInput = ({
  input,
  onInputChange,
  onKeyDown,
  onSubmit,
  onToggleInfo,
  disabled,
}) => {
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef(null)

  useEffect(() => {
    // ブラウザの音声認識APIの互換性チェック
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition()
      recognition.lang = 'ja-JP'
      recognition.continuous = false
      recognition.interimResults = false

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        // 既存の入力がある場合はスペースを空けて追記
        const newValue = input ? `${input} ${transcript}` : transcript
        // 親コンポーネントのステート更新関数を模倣したイベントオブジェクトを作成
        onInputChange({ target: { value: newValue } })
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
    <div className="chat-input">
      <button
        type="button"
        id="information"
        className="btn-info original-btn"
        onClick={onToggleInfo}
        aria-label="入力例を表示"
      >
        <i className="bi bi-info-circle-fill" aria-hidden />
      </button>

      <form className="chat-form" onSubmit={onSubmit}>
        <button
          type="button"
          className={`btn-icon original-btn ${isListening ? 'listening' : ''}`}
          onClick={handleMicClick}
          aria-label="音声入力"
          disabled={disabled}
        >
          <i className={`bi ${isListening ? 'bi-mic-mute-fill' : 'bi-mic-fill'}`} aria-hidden />
        </button>

        <textarea
          id="message"
          name="message"
          placeholder={isListening ? '聞いています...' : 'メッセージを入力...'}
          rows="1"
          maxLength={3000}
          value={input}
          onChange={onInputChange}
          onKeyDown={onKeyDown}
        />
        <button
          type="submit"
          className="btn-chat original-btn"
          disabled={disabled}
          aria-label="送信"
        >
          <i className="bi bi-send-fill" aria-hidden />
        </button>
      </form>
    </div>
  )
}

export default ChatInput
