/**
 * EN: Provide the PlanViewer module implementation.
 * JP: PlanViewer モジュールの実装を定義する。
 */
import { useMemo, useRef, useState } from 'react'
import html2canvas from 'html2canvas'
import './Plan.css'

/**
 * EN: Define the PlanViewerProps type alias.
 * JP: PlanViewerProps 型エイリアスを定義する。
 */
type PlanViewerProps = {
  plan: string
  isSubmitting?: boolean
  onSubmit?: () => void
  showSubmit?: boolean
  className?: string
}

/**
 * EN: Declare the PlanViewer value.
 * JP: PlanViewer の値を宣言する。
 */
const PlanViewer = ({
  plan,
  isSubmitting = false,
  onSubmit,
  showSubmit = true,
  className = '',
}: PlanViewerProps) => {
  const [showSummary, setShowSummary] = useState(false)
  const [actionMessage, setActionMessage] = useState('')
  /**
   * EN: Declare the decisionCardRef value.
   * JP: decisionCardRef の値を宣言する。
   */
  const decisionCardRef = useRef<HTMLDivElement | null>(null)
  /**
   * EN: Declare the planLines value.
   * JP: planLines の値を宣言する。
   */
  const planLines = useMemo(
    () => {
      if (!plan) return []
      // Replace <br> or <br/> tags with newlines to ensure correct splitting
      /**
       * EN: Declare the sanitizedPlan value.
       * JP: sanitizedPlan の値を宣言する。
       */
      const sanitizedPlan = plan.replace(/<br\s*\/?>/gi, '\n')
      return sanitizedPlan.split('\n').map((line) => line.trim()).filter(Boolean)
    },
    [plan]
  )

  /**
   * EN: Declare the resetActionMessage value.
   * JP: resetActionMessage の値を宣言する。
   */
  const resetActionMessage = () => {
    setActionMessage('')
  }

  /**
   * EN: Declare the downloadBlob value.
   * JP: downloadBlob の値を宣言する。
   */
  const downloadBlob = (blob: Blob, filename: string) => {
    /**
     * EN: Declare the url value.
     * JP: url の値を宣言する。
     */
    const url = URL.createObjectURL(blob)
    /**
     * EN: Declare the link value.
     * JP: link の値を宣言する。
     */
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }

  /**
   * EN: Declare the formatTimestamp value.
   * JP: formatTimestamp の値を宣言する。
   */
  const formatTimestamp = () => {
    /**
     * EN: Declare the now value.
     * JP: now の値を宣言する。
     */
    const now = new Date()
    /**
     * EN: Declare the pad value.
     * JP: pad の値を宣言する。
     */
    const pad = (value: number) => String(value).padStart(2, '0')
    return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  }

  /**
   * EN: Declare the handleDecide value.
   * JP: handleDecide の値を宣言する。
   */
  const handleDecide = () => {
    if (!plan || isSubmitting) {
      return
    }
    setShowSummary(true)
    resetActionMessage()
    onSubmit?.()
  }

  /**
   * EN: Declare the handleSaveImage value.
   * JP: handleSaveImage の値を宣言する。
   */
  const handleSaveImage = async () => {
    if (!decisionCardRef.current) return
    try {
      /**
       * EN: Declare the canvas value.
       * JP: canvas の値を宣言する。
       */
      const canvas = await html2canvas(decisionCardRef.current, {
        backgroundColor: '#ffffff',
        scale: 2
      })
      /**
       * EN: Declare the blob value.
       * JP: blob の値を宣言する。
       */
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, 'image/png'),
      )
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

  /**
   * EN: Declare the handleSaveText value.
   * JP: handleSaveText の値を宣言する。
   */
  const handleSaveText = () => {
    try {
      /**
       * EN: Declare the text value.
       * JP: text の値を宣言する。
       */
      const text = planLines.join('\n')
      /**
       * EN: Declare the blob value.
       * JP: blob の値を宣言する。
       */
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      downloadBlob(blob, `decision-summary-${formatTimestamp()}.txt`)
      setActionMessage('テキストとして保存しました。')
    } catch (error) {
      console.error('Save text failed:', error)
      setActionMessage('テキストの保存に失敗しました。')
    }
  }

  /**
   * EN: Declare the handleCopy value.
   * JP: handleCopy の値を宣言する。
   */
  const handleCopy = async () => {
    try {
      /**
       * EN: Declare the text value.
       * JP: text の値を宣言する。
       */
      const text = planLines.join('\n')
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        /**
         * EN: Declare the textarea value.
         * JP: textarea の値を宣言する。
         */
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
      <div className={`card chat-card ${className}`}>
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
