/**
 * EN: Provide the usePlan module implementation.
 * JP: usePlan モジュールの実装を定義する。
 */
import { useState } from 'react'
import { apiUrl } from '../utils/apiBase'
import type { ApiErrorResponse, PlanSummaryResponse, ReservationDataItem } from '../types/api'
import type { AppError } from '../types/error'
import { normalizeAppError, toFrontendAppError } from '../utils/errorHandling'

type UsePlanOptions = {
  submitEndpoint: string
  addSystemMessage?: (text: string) => void
  fetchSummaryAfterSubmit?: boolean
  onSuccess?: () => void
  onError?: (error: AppError) => void
}

const summaryFieldLabels: Array<[string, keyof ReservationDataItem]> = [
  ['目的地', 'destinations'],
  ['出発地', 'departure'],
  ['ホテル', 'hotel'],
  ['航空会社', 'airlines'],
  ['鉄道会社', 'railway'],
  ['タクシー会社', 'taxi'],
  ['滞在開始日', 'start_date'],
  ['滞在終了日', 'end_date'],
]

const formatReservationSummary = (items: ReservationDataItem[] | undefined): string | null => {
  if (!items || items.length === 0) return null

  const lines = items.flatMap((item) =>
    summaryFieldLabels
      .map(([label, key]) => {
        const value = item[key]
        return typeof value === 'string' && value.trim() ? `${label}：${value}` : null
      })
      .filter((line): line is string => Boolean(line)),
  )
  return lines.length ? lines.join(' / ') : null
}

/**
 * EN: Declare the usePlan value.
 * JP: usePlan の値を宣言する。
 */
export const usePlan = ({
  submitEndpoint,
  addSystemMessage,
  fetchSummaryAfterSubmit = false,
  onSuccess,
  onError,
}: UsePlanOptions) => {
  const [currentPlan, setCurrentPlan] = useState('')
  const [submittingPlan, setSubmittingPlan] = useState(false)

  /**
   * EN: Declare the submitPlan value.
   * JP: submitPlan の値を宣言する。
   */
  const submitPlan = async () => {
    if (!currentPlan?.trim() || submittingPlan) return

    setSubmittingPlan(true)
    try {
      /**
       * EN: Declare the response value.
       * JP: response の値を宣言する。
       */
      const response = await fetch(apiUrl(submitEndpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: currentPlan }),
        credentials: 'include',
      })

      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as ApiErrorResponse | null
        throw toFrontendAppError(data, response.status, 'プランの保存に失敗しました。')
      }

      let summary: PlanSummaryResponse | null = null
      if (fetchSummaryAfterSubmit) {
        try {
          /**
           * EN: Declare the summaryResponse value.
           * JP: summaryResponse の値を宣言する。
           */
          const summaryResponse = await fetch(apiUrl('/complete'), {
            headers: { Accept: 'application/json' },
            credentials: 'include',
          })
          if (summaryResponse.ok) {
            summary = (await summaryResponse.json()) as PlanSummaryResponse
          }
        } catch (error) {
          console.warn('Failed to fetch summary:', error)
        }
      }

      if (addSystemMessage) {
        addSystemMessage('決定したプランを保存しました。')

        const formattedSummary = formatReservationSummary(summary?.reservation_data)
        if (formattedSummary) {
          addSystemMessage(formattedSummary)
        }
      }

      onSuccess?.()
    } catch (error) {
      console.error('SubmitPlan Error:', error)
      const appError = normalizeAppError(error)
      if (addSystemMessage) {
        addSystemMessage(appError.message)
      }
      onError?.(appError)
    } finally {
      setSubmittingPlan(false)
    }
  }

  return {
    currentPlan,
    setCurrentPlan,
    submittingPlan,
    submitPlan,
  }
}
