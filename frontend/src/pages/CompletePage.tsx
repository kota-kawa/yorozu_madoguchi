/**
 * EN: Provide the CompletePage module implementation.
 * JP: CompletePage モジュールの実装を定義する。
 */
import { useEffect, useState } from 'react'
import Header from '../components/Header/Header'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import './CompletePage.css'
import { apiUrl } from '../utils/apiBase'
import { clearAllPersistedChatStates } from '../hooks/useGenericChat'
import type { PlanSummaryResponse, ReservationDataItem } from '../types/api'

const reservationLabels: Array<[string, keyof ReservationDataItem]> = [
  ['目的地', 'destinations'],
  ['出発地', 'departure'],
  ['ホテル', 'hotel'],
  ['航空会社', 'airlines'],
  ['鉄道会社', 'railway'],
  ['タクシー会社', 'taxi'],
  ['滞在開始日', 'start_date'],
  ['滞在終了日', 'end_date'],
]

const isReservationDataItem = (value: unknown): value is ReservationDataItem => {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>

  const id = record.id
  const sessionId = record.session_id
  if (!Number.isInteger(id) || typeof sessionId !== 'string') return false

  return reservationLabels.every(([, key]) => {
    const field = record[key]
    return field === null || typeof field === 'string'
  })
}

const formatReservationItem = (item: ReservationDataItem): string[] =>
  reservationLabels.flatMap(([label, key]) => {
    const value = item[key]
    if (typeof value !== 'string') return []
    const text = value.trim()
    return text ? [`${label}：${text}`] : []
  })

/**
 * EN: Declare the CompletePage value.
 * JP: CompletePage の値を宣言する。
 */
const CompletePage = () => {
  const [loading, setLoading] = useState(true)
  const [reservationData, setReservationData] = useState<string[]>([])
  const [error, setError] = useState('')
  const [startingNewSession, setStartingNewSession] = useState(false)

  useEffect(() => {
    /**
     * EN: Declare the controller value.
     * JP: controller の値を宣言する。
     */
    const controller = new AbortController()
    /**
     * EN: Declare the fetchSummary value.
     * JP: fetchSummary の値を宣言する。
     */
    const fetchSummary = async () => {
      try {
        /**
         * EN: Declare the response value.
         * JP: response の値を宣言する。
         */
        const response = await fetch(apiUrl('/complete'), {
          headers: { Accept: 'application/json' },
          credentials: 'include',
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error('予約内容の取得に失敗しました。')
        }

        /**
         * EN: Declare the data value.
         * JP: data の値を宣言する。
         */
        const data = (await response.json()) as PlanSummaryResponse
        /**
         * EN: Declare the items value.
         * JP: items の値を宣言する。
         */
        const items = Array.isArray(data?.reservation_data) ? data.reservation_data : []
        const normalized = items
          .filter(isReservationDataItem)
          .flatMap((item) => formatReservationItem(item))

        setReservationData(normalized)
      } catch (err) {
        /**
         * EN: Declare the isAbort value.
         * JP: isAbort の値を宣言する。
         */
        const isAbort = err instanceof DOMException && err.name === 'AbortError'
        if (!isAbort) {
          setError('予約内容の取得に失敗しました。')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchSummary()
    return () => controller.abort()
  }, [])

  const handleStartNewSession = async () => {
    if (startingNewSession) return
    setStartingNewSession(true)
    try {
      const response = await fetch(apiUrl('/api/reset'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_session: true }),
        credentials: 'include',
      })
      if (!response.ok) {
        throw new Error('新しいセッションの作成に失敗しました。')
      }
      clearAllPersistedChatStates()
      window.location.assign('/')
    } catch (err) {
      const message =
        err instanceof Error && err.message.trim() ? err.message : '新しいセッションの作成に失敗しました。'
      setError(message)
      setStartingNewSession(false)
    }
  }

  return (
    <div className="app complete-page">
      <Header
        subtitle="予約完了"
        onStartNewSession={handleStartNewSession}
        isStartingNewSession={startingNewSession}
      />

      <main className="complete-content">
        <section className="card complete-card">
          <div className="complete-header">
            <h2>予約完了</h2>
            <p>ご予約ありがとうございます！以下の内容で予約が完了しました。</p>
          </div>

          <div className="complete-body">
            {error && <p className="complete-error">{error}</p>}
            {!error && !reservationData.length && (
              <p className="complete-empty">予約情報がまだ登録されていません。</p>
            )}
            {!!reservationData.length && (
              <ul className="complete-list">
                {reservationData.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="complete-footer">
            ご不明な点がございましたら、サポートまでご連絡ください。
          </div>
        </section>
      </main>

      <LoadingSpinner visible={loading} />
    </div>
  )
}

export default CompletePage
