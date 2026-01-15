import { useMemo, useState } from 'react'
import './Plan.css'

const PlanViewer = ({ plan, isSubmitting, onSubmit, showSubmit = true }) => {
  const [showSummary, setShowSummary] = useState(false)
  const planLines = useMemo(
    () => (plan ? plan.split('\n').map((line) => line.trim()).filter(Boolean) : []),
    [plan]
  )

  const handleDecide = () => {
    if (!plan || isSubmitting) {
      return
    }
    setShowSummary(true)
    onSubmit?.()
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
              <button
                type="button"
                className="decision-dismiss"
                onClick={() => setShowSummary(false)}
              >
                閉じる
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}

export default PlanViewer
