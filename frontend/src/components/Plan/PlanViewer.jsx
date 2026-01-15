import { useMemo, useRef, useState } from 'react'
import html2canvas from 'html2canvas'
import './Plan.css'

const PlanViewer = ({ plan, isSubmitting, onSubmit, showSubmit = true }) => {
  const [showSummary, setShowSummary] = useState(false)
  const [actionMessage, setActionMessage] = useState('')
  const decisionCardRef = useRef(null)
  const planLines = useMemo(
    () => (plan ? plan.split('\n').map((line) => line.trim()).filter(Boolean) : []),
    [plan]
  )

  const resetActionMessage = () => {
    setActionMessage('')
  }

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  const formatTimestamp = () => {
    const now = new Date()
    const pad = (value) => String(value).padStart(2, '0')
    return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  }

  const handleDecide = () => {
    if (!plan || isSubmitting) {
      return
    }
    setShowSummary(true)
    resetActionMessage()
    onSubmit?.()
  }

  const handleSaveImage = async () => {
    if (!decisionCardRef.current) return
    try {
      const canvas = await html2canvas(decisionCardRef.current, {
        backgroundColor: '#ffffff',
        scale: 2
      })
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
      if (!blob) {
        throw new Error('Failed to create image')
      }
      downloadBlob(blob, `decision-summary-${formatTimestamp()}.png`)
      setActionMessage('画像として保存しました。')
    } catch (error) {
      console.error('Save image failed:', error)
      setActionMessage('画像の保存に失敗しました。')
    }
  }

  const handleSaveText = () => {
    try {
      const text = planLines.join('\n')
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      downloadBlob(blob, `decision-summary-${formatTimestamp()}.txt`)
      setActionMessage('テキストとして保存しました。')
    } catch (error) {
      console.error('Save text failed:', error)
      setActionMessage('テキストの保存に失敗しました。')
    }
  }

  const handleCopy = async () => {
    try {
      const text = planLines.join('\n')
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        textarea.remove()
      }
      setActionMessage('コピーしました。')
    } catch (error) {
      console.error('Copy failed:', error)
      setActionMessage('コピーに失敗しました。')
    }
  }

  return (
    <>
      <div className="card chat-card">
        <div className="card-header">
          <h1>決定している状況</h1>
        </div>
        <div className="card-body chat-messages plan-body">
          {plan ? (
            planLines.map((line, index) => (
              <p key={`${line}-${index}`} className="fade-in">
                {line}
              </p>
            ))
          ) : (
            <p className="muted">まだ決定事項はありません。</p>
          )}
        </div>
        {showSubmit ? (
          <div className="card-footer">
            <div className="bottom-right-content">
              <button
                type="button"
                className="btn-decide"
                id="sendBu"
                onClick={handleDecide}
                disabled={!plan || isSubmitting}
              >
                <i className="bi bi-check-circle-fill" aria-hidden /> 決定
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {showSummary ? (
        <div
          className="decision-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="決定内容のまとめ"
          onClick={() => setShowSummary(false)}
        >
          <div
            className="decision-card"
            ref={decisionCardRef}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="decision-card-header">
              <span className="decision-title">決定内容のまとめ</span>
              <button
                type="button"
                className="decision-close"
                onClick={() => setShowSummary(false)}
                aria-label="閉じる"
              >
                x
              </button>
            </div>
            <div className="decision-card-body">
              {planLines.length ? (
                <ul className="decision-list">
                  {planLines.map((line, index) => (
                    <li key={`${line}-${index}`}>{line}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted">決定内容がありません。</p>
              )}
            </div>
            <div className="decision-card-footer">
              <div className="decision-actions">
                <button
                  type="button"
                  className="decision-action-btn"
                  onClick={handleSaveImage}
                  disabled={!planLines.length}
                >
                  画像で保存
                </button>
                <button
                  type="button"
                  className="decision-action-btn"
                  onClick={handleSaveText}
                  disabled={!planLines.length}
                >
                  テキストで保存
                </button>
                <button
                  type="button"
                  className="decision-action-btn"
                  onClick={handleCopy}
                  disabled={!planLines.length}
                >
                  コピー
                </button>
                <button
                  type="button"
                  className="decision-dismiss"
                  onClick={() => setShowSummary(false)}
                >
                  閉じる
                </button>
              </div>
              {actionMessage ? (
                <p className="decision-action-message">{actionMessage}</p>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

export default PlanViewer
