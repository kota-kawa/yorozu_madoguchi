/**
 * EN: Provide the InfoPanel module implementation.
 * JP: InfoPanel モジュールの実装を定義する。
 */
import { createPortal } from 'react-dom'
import { useEffect, useState } from 'react'
import './UI.css'

/**
 * EN: Define the InfoPanelProps type alias.
 * JP: InfoPanelProps 型エイリアスを定義する。
 */
type InfoPanelProps = {
  isOpen: boolean
  samples: string[]
  onSelect: (value: string) => void
  onClose: () => void
}

/**
 * EN: Declare the InfoPanel value.
 * JP: InfoPanel の値を宣言する。
 */
const InfoPanel = ({ isOpen, samples, onSelect, onClose }: InfoPanelProps) => {
  const [isMounted, setIsMounted] = useState(isOpen)
  const [isClosing, setIsClosing] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setIsMounted(true)
      setIsClosing(false)
      return
    }

    if (!isMounted) return

    setIsClosing(true)
    const timer = window.setTimeout(() => {
      setIsMounted(false)
      setIsClosing(false)
    }, 200)

    return () => {
      window.clearTimeout(timer)
    }
  }, [isOpen, isMounted])

  if (!isMounted) return null

  const panelClassName = `info-text ${isClosing ? 'closing' : 'open'}`
  const overlayClassName = `info-overlay${isClosing ? ' closing' : ''}`

  return createPortal(
    <>
      <div className={overlayClassName} onClick={onClose} />
      <div className={panelClassName} onClick={(e) => e.stopPropagation()}>
        <h2>入力の例</h2>
        <div className="option-list">
          {samples.map((sample) => (
            <button
              key={sample}
              type="button"
              className="sample-option"
              onClick={(e) => {
                e.stopPropagation()
                onSelect(sample)
                onClose()
              }}
            >
              {sample}
            </button>
          ))}
        </div>
      </div>
    </>,
    document.body
  )
}

export default InfoPanel
