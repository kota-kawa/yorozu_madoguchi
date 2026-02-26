/**
 * EN: Provide the LoadingSpinner module implementation.
 * JP: LoadingSpinner モジュールの実装を定義する。
 */
import './UI.css'

/**
 * EN: Define the LoadingSpinnerProps type alias.
 * JP: LoadingSpinnerProps 型エイリアスを定義する。
 */
type LoadingSpinnerProps = {
  visible: boolean
  variant?: 'overlay' | 'inline'
}

/**
 * EN: Declare the LoadingSpinner value.
 * JP: LoadingSpinner の値を宣言する。
 */
const LoadingSpinner = ({ visible, variant = 'overlay' }: LoadingSpinnerProps) => {
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
