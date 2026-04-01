import { useEffect } from 'react'
import './UI.css'

type ErrorToastProps = {
  message: string
  visible: boolean
  onClose: () => void
  autoHideMs?: number
}

const ErrorToast = ({ message, visible, onClose, autoHideMs = 4500 }: ErrorToastProps) => {
  useEffect(() => {
    if (!visible) return
    const timerId = window.setTimeout(() => onClose(), autoHideMs)
    return () => window.clearTimeout(timerId)
  }, [visible, onClose, autoHideMs])

  if (!visible) return null

  return (
    <div className="error-toast" role="alert" aria-live="assertive">
      <div className="error-toast-content">
        <span className="error-toast-icon" aria-hidden="true">
          <i className="bi bi-exclamation-triangle-fill" />
        </span>
        <span className="error-toast-message">{message}</span>
      </div>
      <button type="button" className="error-toast-close" onClick={onClose} aria-label="エラーメッセージを閉じる">
        <i className="bi bi-x-lg" aria-hidden="true" />
      </button>
    </div>
  )
}

export default ErrorToast

