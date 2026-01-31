import { useEffect, useState } from 'react'
import Header from '../components/Header/Header'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import './CompletePage.css'

type ReservationSummaryResponse = {
  reservation_data?: unknown
}

type ReservationItem = {
  destinations?: string
  departure?: string
  hotel?: string
  airlines?: string
  railway?: string
  taxi?: string
  start_date?: string
  end_date?: string
}

const CompletePage = () => {
  const [loading, setLoading] = useState(true)
  const [reservationData, setReservationData] = useState<string[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    const fetchSummary = async () => {
      try {
        const response = await fetch('/complete', {
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error('予約内容の取得に失敗しました。')
        }

        const data = (await response.json()) as ReservationSummaryResponse
        const items = Array.isArray(data?.reservation_data) ? data.reservation_data : []
        const normalized = items.flatMap((item) => {
          if (typeof item === 'string') return [item]
          if (!item || typeof item !== 'object') return [String(item)]

          const record = item as ReservationItem
          const fields: Array<[string, string | undefined]> = [
            ['目的地', record.destinations],
            ['出発地', record.departure],
            ['ホテル', record.hotel],
            ['航空会社', record.airlines],
            ['鉄道会社', record.railway],
            ['タクシー会社', record.taxi],
            ['滞在開始日', record.start_date],
            ['滞在終了日', record.end_date],
          ]
          return fields
            .filter(([, value]) => value)
            .map(([label, value]) => `${label}：${value}`)
        })

        setReservationData(normalized)
      } catch (err) {
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

  return (
    <div className="app complete-page">
      <Header
        subtitle="予約完了"
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
