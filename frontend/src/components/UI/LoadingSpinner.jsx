import './UI.css'

const LoadingSpinner = ({ visible, variant = 'overlay' }) => {
  if (!visible) return null

  if (variant === 'inline') {
    return (
      <div className="spinner-inline" role="status" aria-live="polite">
        <div className="spinner-border">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    )
  }

  return (
    <div id="spinnerOverlay" role="status">
      <div className="spinner-border">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  )
}

export default LoadingSpinner
