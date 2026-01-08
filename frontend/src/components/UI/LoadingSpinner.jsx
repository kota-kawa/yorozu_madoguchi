import './UI.css'

const LoadingSpinner = ({ visible }) => {
  if (!visible) return null
  return (
    <div id="spinnerOverlay" role="status">
      <div className="spinner-border">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  )
}

export default LoadingSpinner
