/**
 * EN: Provide the UserTypeGate module implementation.
 * JP: UserTypeGate モジュールの実装を定義する。
 */
import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import './UserTypeGate.css'
import { apiUrl } from '../../utils/apiBase'
import { getStoredUserType, setStoredUserType } from '../../utils/userType'

/**
 * EN: Define the UserType type alias.
 * JP: UserType 型エイリアスを定義する。
 */
type UserType = '' | 'normal' | 'premium'
/**
 * EN: Define the GateStatus type alias.
 * JP: GateStatus 型エイリアスを定義する。
 */
type GateStatus = 'syncing' | 'idle' | 'ready' | 'error'
/**
 * EN: Define the UserTypeGateProps type alias.
 * JP: UserTypeGateProps 型エイリアスを定義する。
 */
type UserTypeGateProps = {
  children: ReactNode
}

/**
 * EN: Define the UserTypeResponse type alias.
 * JP: UserTypeResponse 型エイリアスを定義する。
 */
type UserTypeResponse = {
  error?: string
}

/**
 * EN: Declare the SYNC_TIMEOUT_MS value.
 * JP: SYNC_TIMEOUT_MS の値を宣言する。
 */
const SYNC_TIMEOUT_MS = 15000

/**
 * EN: Declare the UserTypeGate value.
 * JP: UserTypeGate の値を宣言する。
 */
const UserTypeGate = ({ children }: UserTypeGateProps) => {
  const [userType, setUserType] = useState<UserType>(getStoredUserType)
  const [status, setStatus] = useState<GateStatus>(userType ? 'syncing' : 'idle')
  const [error, setError] = useState('')
  /**
   * EN: Declare the lastSyncedRef value.
   * JP: lastSyncedRef の値を宣言する。
   */
  const lastSyncedRef = useRef('')
  /**
   * EN: Declare the inFlightRef value.
   * JP: inFlightRef の値を宣言する。
   */
  const inFlightRef = useRef<AbortController | null>(null)
  /**
   * EN: Declare the requestIdRef value.
   * JP: requestIdRef の値を宣言する。
   */
  const requestIdRef = useRef(0)
  /**
   * EN: Declare the mountedRef value.
   * JP: mountedRef の値を宣言する。
   */
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      inFlightRef.current?.abort()
    }
  }, [])

  /**
   * EN: Declare the syncUserType value.
   * JP: syncUserType の値を宣言する。
   */
  const syncUserType = async (nextUserType: UserType) => {
    /**
     * EN: Declare the requestId value.
     * JP: requestId の値を宣言する。
     */
    const requestId = ++requestIdRef.current
    inFlightRef.current?.abort()
    /**
     * EN: Declare the supportsAbort value.
     * JP: supportsAbort の値を宣言する。
     */
    const supportsAbort = typeof AbortController !== 'undefined'
    /**
     * EN: Declare the controller value.
     * JP: controller の値を宣言する。
     */
    const controller = supportsAbort ? new AbortController() : null
    inFlightRef.current = controller
    setStatus('syncing')
    setError('')
    /**
     * EN: Declare the timeoutId value.
     * JP: timeoutId の値を宣言する。
     */
    const timeoutId = window.setTimeout(() => {
      if (!mountedRef.current) return
      if (requestIdRef.current !== requestId) return
      requestIdRef.current += 1
      controller?.abort()
      setStatus('error')
      setError('通信がタイムアウトしました。再試行してください。')
    }, SYNC_TIMEOUT_MS)
    try {
      /**
       * EN: Declare the response value.
       * JP: response の値を宣言する。
       */
      const response = await fetch(apiUrl('/api/user_type'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_type: nextUserType }),
        credentials: 'include',
        ...(controller ? { signal: controller.signal } : {}),
      })
      /**
       * EN: Declare the data value.
       * JP: data の値を宣言する。
       */
      const data = (await response.json().catch(() => null)) as UserTypeResponse | null
      if (!response.ok) {
        throw new Error(data?.error || 'ユーザー種別の登録に失敗しました。')
      }
      if (!mountedRef.current || requestId !== requestIdRef.current) return
      lastSyncedRef.current = nextUserType
      setStatus('ready')
    } catch (err) {
      if (!mountedRef.current || requestId !== requestIdRef.current) return
      setStatus('error')
      /**
       * EN: Declare the message value.
       * JP: message の値を宣言する。
       */
      const message =
        controller?.signal.aborted
          ? '通信がタイムアウトしました。再試行してください。'
          : err instanceof Error
            ? err.message
            : 'ユーザー種別の登録に失敗しました。'
      setError(message)
    } finally {
      window.clearTimeout(timeoutId)
      if (inFlightRef.current === controller) {
        inFlightRef.current = null
      }
    }
  }

  useEffect(() => {
    if (!userType) return
    if (lastSyncedRef.current === userType && status === 'ready') return
    syncUserType(userType)
  }, [userType])

  /**
   * EN: Declare the handleSelect value.
   * JP: handleSelect の値を宣言する。
   */
  const handleSelect = (nextType: UserType) => {
    if (!nextType) return
    setStoredUserType(nextType)
    setUserType(nextType)
  }

  /**
   * EN: Declare the handleRetry value.
   * JP: handleRetry の値を宣言する。
   */
  const handleRetry = () => {
    if (!userType) return
    syncUserType(userType)
  }

  /**
   * EN: Declare the handleCancel value.
   * JP: handleCancel の値を宣言する。
   */
  const handleCancel = () => {
    requestIdRef.current += 1
    inFlightRef.current?.abort()
    inFlightRef.current = null
    setStoredUserType('')
    setUserType('')
    setStatus('idle')
    setError('')
  }

  /**
   * EN: Declare the shouldBlock value.
   * JP: shouldBlock の値を宣言する。
   */
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
                  <span className="option-meta">1日50回まで</span>
                  <span className="option-desc">お試しやライトな利用におすすめ</span>
                </button>
                <button type="button" className="user-type-option premium" onClick={() => handleSelect('premium')}>
                  <span className="option-title">プレミアムユーザー</span>
                  <span className="option-meta">1日150回まで</span>
                  <span className="option-desc">本格的に使いたい方はこちら</span>
                </button>
              </div>
            )}

            {status === 'syncing' && (
              <div className="user-type-status">
                <div className="user-type-spinner" aria-hidden="true" />
                <p>ユーザー種別を登録しています...</p>
                <button type="button" className="user-type-back" onClick={handleCancel}>
                  選択し直す
                </button>
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
