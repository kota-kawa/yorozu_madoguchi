import { useEffect, useState } from 'react'
import Header from '../components/Header/Header'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import './CompletePage.css'

const CompletePage = () => {
  const [loading, setLoading] = useState(true)
  const [reservationData, setReservationData] = useState([])
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

        const data = await response.json()
        const items = data?.reservation_data ?? []
        const normalized = items.flatMap((item) => {
          if (typeof item === 'string') return [item]
          if (!item || typeof item !== 'object') return [String(item)]

          const fields = [
            ['目的地', item.destinations],
            ['出発地', item.departure],
            ['ホテル', item.hotel],
            ['航空会社', item.airlines],
            ['鉄道会社', item.railway],
            ['タクシー会社', item.taxi],
            ['滞在開始日', item.start_date],
            ['滞在終了日', item.end_date],
          ]
          return fields
            .filter(([, value]) => value)
            .map(([label, value]) => `${label}：${value}`)
        })

        setReservationData(normalized)
      } catch (err) {
        if (err.name !== 'AbortError') {
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
                  <li key={`${item.id || 'item'}-${index}`}>{item}</li>
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
