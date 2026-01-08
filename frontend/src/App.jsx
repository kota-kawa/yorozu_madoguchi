import { useEffect, useRef, useState } from 'react'
import './App.css'

const SAMPLE_PROMPTS = [
  'どこに行くのがおすすめ？',
  'どんな有名スポットがある？',
  '落ち着ける場所はある？',
  'ご飯に行くならどこ？',
]

const initialMessage = {
  id: 'welcome',
  sender: 'bot',
  text: 'どんな旅行の計画を一緒に立てますか？😊',
}

function App() {
  const [messages, setMessages] = useState([initialMessage])
  const [input, setInput] = useState('')
  const [currentPlan, setCurrentPlan] = useState('')
  const [infoOpen, setInfoOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [submittingPlan, setSubmittingPlan] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/reset', { method: 'POST', signal: controller.signal }).catch(() => {})
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, autoScroll])

  const handleScroll = (event) => {
    const target = event.currentTarget
    const isAtBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 10
    setAutoScroll(isAtBottom)
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit(event)
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    sendMessage(input)
  }

  const handleYesNo = (response) => {
    sendMessage(response)
  }

  const sendMessage = async (text) => {
    const trimmed = text.trim()
    if (!trimmed) return

    if (trimmed.length > 3000) {
      alert('入力された文字数が3000文字を超えています。3000文字以内で入力してください。')
      return
    }

    const userMessage = { id: `user-${Date.now()}`, sender: 'user', text: trimmed }
    const loadingMessage = {
      id: `loading-${Date.now()}`,
      sender: 'bot',
      text: '回答を考えています...',
      pending: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setInput('')
    setLoading(true)
    try {
      const response = await fetch('/travel_send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
      })

      if (!response.ok) {
        throw new Error(`Server Error: ${response.status}`)
      }

      const data = await response.json()

      if (data.error) {
         throw new Error(data.response || 'API Error')
      }

      const remainingText = data?.remaining_text
      const hasRemainingText =
        remainingText !== null && remainingText !== undefined && remainingText !== 'Empty'
      const botText = hasRemainingText ? remainingText : data?.response

      const updates = []
      if (botText) {
        updates.push({ id: `bot-${Date.now()}`, sender: 'bot', text: botText })
      }
      if (data?.yes_no_phrase) {
        updates.push({
          id: `yesno-${Date.now()}`,
          sender: 'bot',
          text: data.yes_no_phrase,
          type: 'yesno',
        })
      }

      setMessages((prev) => {
        const withoutPending = prev.filter(
          (message) => message.id !== loadingMessage.id && message.type !== 'yesno',
        )
        return [...withoutPending, ...updates]
      })

      if (data?.current_plan !== undefined) {
        setCurrentPlan(data.current_plan)
      }
    } catch (error) {
      console.error("SendMessage Error:", error)
      setMessages((prev) =>
        prev
          .filter((message) => message.id !== loadingMessage.id)
          .concat({
            id: `error-${Date.now()}`,
            sender: 'bot',
            text: 'サーバーからの応答に失敗しました。時間をおいて再試行してください。',
          }),
      )
    } finally {
      setLoading(false)
    }
  }

  const submitPlan = async () => {
    if (!currentPlan?.trim()) {
      return
    }

    setSubmittingPlan(true)
    try {
      const response = await fetch('/travel_submit_plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: currentPlan }),
      })

      if (!response.ok) {
        throw new Error('Failed to submit plan')
      }

      let summary = null
      try {
        const summaryResponse = await fetch('/complete', {
          headers: { Accept: 'application/json' },
        })
        if (summaryResponse.ok) {
          summary = await summaryResponse.json()
        }
      } catch (error) {
        // 予約情報の読み込みは任意
        console.warn("Failed to fetch summary:", error)
      }

      setMessages((prev) => [
        ...prev,
        { id: `confirm-${Date.now()}`, sender: 'bot', text: '決定したプランを保存しました。' },
      ])

      if (summary?.reservation_data?.length) {
        setMessages((prev) => [
          ...prev,
          {
            id: `summary-${Date.now()}`,
            sender: 'bot',
            text: summary.reservation_data.join(' / '),
          },
        ])
      }
    } catch (error) {
      console.error("SubmitPlan Error:", error)
      setMessages((prev) => [
        ...prev,
        { id: `error-submit-${Date.now()}`, sender: 'bot', text: 'プランの保存に失敗しました。' },
      ])
    } finally {
      setSubmittingPlan(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>よろずの窓口</h1>
        <p className="subtitle">React フロントエンド ＋ Flask API</p>
      </header>

      <div className="chat-container">
        <div className="card chat-card">
          <div className="card-body chat-messages" onScroll={handleScroll}>
            {messages.map((message) => (
              <div key={message.id} className={`chat-message ${message.sender}`}>
                <p>{message.text}</p>
                {message.type === 'yesno' && (
                  <div className="button-container">
                    <button
                      type="button"
                      className="btn btn-yes"
                      onClick={() => handleYesNo('はい')}
                      disabled={loading || submittingPlan}
                    >
                      はい　<i className="bi bi-hand-thumbs-up-fill" aria-hidden />
                    </button>
                    <button
                      type="button"
                      className="btn btn-no"
                      onClick={() => handleYesNo('いいえ')}
                      disabled={loading || submittingPlan}
                    >
                      いいえ <i className="bi bi-hand-thumbs-down-fill" aria-hidden />
                    </button>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="card-footer">
            <div className={`info-text ${infoOpen ? 'open' : ''}`}>
              <h2>入力の例</h2>
              <div className="option-list">
                {SAMPLE_PROMPTS.map((sample) => (
                  <button
                    key={sample}
                    type="button"
                    className="sample-option"
                    onClick={() => setInput(sample)}
                  >
                    {sample}
                  </button>
                ))}
              </div>
            </div>

            <div className="chat-input">
              <button
                type="button"
                id="information"
                className="btn-info original-btn"
                onClick={() => setInfoOpen((prev) => !prev)}
                aria-label="入力例を表示"
              >
                <i className="bi bi-info-circle-fill" aria-hidden />
              </button>

              <form className="chat-form" onSubmit={handleSubmit}>
                <textarea
                  id="message"
                  name="message"
                  placeholder="メッセージを入力．．．"
                  rows="1"
                  maxLength={3000}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleKeyDown}
                />
                <button
                  type="submit"
                  className="btn-chat original-btn"
                  disabled={loading || submittingPlan}
                  aria-label="送信"
                >
                  <i className="bi bi-send-fill" aria-hidden />
                </button>
              </form>
            </div>
          </div>
        </div>

        <div className="card chat-card">
          <div className="card-header">
            <h1>決定している状況</h1>
          </div>
          <div className="card-body chat-messages plan-body">
            {currentPlan ? (
              currentPlan.split('\n').map((line, index) => (
                <p key={`${line}-${index}`} className="fade-in">
                  {line}
                </p>
              ))
            ) : (
              <p className="muted">まだ決定事項はありません。</p>
            )}
          </div>
          <div className="card-footer">
            <div className="bottom-right-content">
              <button
                type="button"
                className="btn-decide"
                id="sendBu"
                onClick={submitPlan}
                disabled={!currentPlan || submittingPlan}
              >
                <i className="bi bi-check-circle-fill" aria-hidden /> 決定
              </button>
            </div>
          </div>
        </div>
      </div>

      {(loading || submittingPlan) && (
        <div id="spinnerOverlay" role="status">
          <div className="spinner-border">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
