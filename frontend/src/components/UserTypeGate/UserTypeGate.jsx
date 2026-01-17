import { useEffect, useRef, useState } from 'react'
import './UserTypeGate.css'
import { getStoredUserType, setStoredUserType } from '../../utils/userType'

const UserTypeGate = ({ children }) => {
  const [userType, setUserType] = useState(getStoredUserType)
  const [status, setStatus] = useState(userType ? 'syncing' : 'idle')
  const [error, setError] = useState('')
  const lastSyncedRef = useRef('')

  const syncUserType = async (nextUserType) => {
    setStatus('syncing')
    setError('')
    try {
      const response = await fetch('/api/user_type', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_type: nextUserType }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(data?.error || 'ユーザー種別の登録に失敗しました。')
      }
      lastSyncedRef.current = nextUserType
      setStatus('ready')
    } catch (err) {
      setStatus('error')
      setError(err?.message || 'ユーザー種別の登録に失敗しました。')
    }
  }

  useEffect(() => {
    if (!userType) return
    if (lastSyncedRef.current === userType && status === 'ready') return
    syncUserType(userType)
  }, [userType])

  const handleSelect = (nextType) => {
    setStoredUserType(nextType)
    setUserType(nextType)
  }

  const handleRetry = () => {
    if (!userType) return
    syncUserType(userType)
  }

  const shouldBlock = status !== 'ready'

  return (
    <>
      {children}
      {shouldBlock && (
        <div className="user-type-overlay" role="dialog" aria-modal="true">
          <div className="user-type-card">
            <div className="user-type-header">
              <p className="user-type-eyebrow">はじめに選択してください</p>
              <h2>ユーザー種別</h2>
              <p className="user-type-subtitle">毎日の入力回数が変わります。</p>
            </div>

            {status === 'idle' && (
              <div className="user-type-options">
                <button type="button" className="user-type-option" onClick={() => handleSelect('normal')}>
                  <span className="option-title">通常ユーザー</span>
                  <span className="option-meta">1日10回まで</span>
                  <span className="option-desc">お試しやライトな利用におすすめ</span>
                </button>
                <button type="button" className="user-type-option premium" onClick={() => handleSelect('premium')}>
                  <span className="option-title">プレミアムユーザー</span>
                  <span className="option-meta">1日100回まで</span>
                  <span className="option-desc">本格的に使いたい方はこちら</span>
                </button>
              </div>
            )}

            {status === 'syncing' && (
              <div className="user-type-status">
                <div className="user-type-spinner" aria-hidden="true" />
                <p>ユーザー種別を登録しています...</p>
              </div>
            )}

            {status === 'error' && (
              <div className="user-type-status">
                <p className="user-type-error">{error}</p>
                <button type="button" className="user-type-retry" onClick={handleRetry}>
                  再試行する
                </button>
                <button type="button" className="user-type-back" onClick={() => setStatus('idle')}>
                  選択し直す
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

export default UserTypeGate
