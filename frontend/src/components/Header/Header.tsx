import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import './Header.css'

type AgentOption = {
  value: string
  label: string
}

const AGENT_OPTIONS: AgentOption[] = [
  { value: '/', label: '旅行計画チャット' },
  { value: '/reply', label: '返信作成アシスタント' },
  { value: '/fitness', label: '筋トレ・フィットネス' },
  { value: '/job', label: '就活アシスタント' },
  { value: '/study', label: '学習アシスタント' },
]

const resolveCurrentAgent = (path: string) => {
  if (path.startsWith('/reply')) return '/reply'
  if (path.startsWith('/fitness')) return '/fitness'
  if (path.startsWith('/job')) return '/job'
  if (path.startsWith('/study')) return '/study'
  return '/'
}

type HeaderProps = {
  title?: string
  subtitle?: string
}

const Header = ({
  title = 'よろずの窓口',
  subtitle = 'React フロントエンド ＋ Flask API',
}: HeaderProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement | null>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const currentAgent = resolveCurrentAgent(location.pathname)
  const currentLabel =
    AGENT_OPTIONS.find((option) => option.value === currentAgent)?.label ||
    AGENT_OPTIONS[0].label

  useEffect(() => {
    const handleOutside = (event: MouseEvent) => {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [])

  const handleSelect = (nextPath: string) => {
    if (nextPath && nextPath !== currentAgent) {
      navigate(nextPath)
    }
    setIsOpen(false)
  }

  return (
    <header className="app-header">
      <div className="header-content">
        <div className="title-container">
          <h1>{title}</h1>
          <p className="subtitle">{subtitle}</p>
        </div>
        <div className="agent-selector">
          <label htmlFor="agent-select" className="agent-label">
            エージェント
          </label>
          <div className="agent-select-wrap" ref={dropdownRef}>
            <button
              type="button"
              className="agent-select"
              id="agent-select"
              aria-haspopup="listbox"
              aria-expanded={isOpen}
              onClick={() => setIsOpen((prev) => !prev)}
            >
              <span>{currentLabel}</span>
            </button>
            {isOpen ? (
              <div className="agent-menu" role="listbox" aria-label="エージェント選択">
                {AGENT_OPTIONS.map((option) => {
                  const isActive = option.value === currentAgent
                  return (
                    <button
                      key={option.value}
                      type="button"
                      role="option"
                      aria-selected={isActive}
                      className={`agent-option${isActive ? ' is-active' : ''}`}
                      onClick={() => handleSelect(option.value)}
                    >
                      {option.label}
                    </button>
                  )
                })}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
