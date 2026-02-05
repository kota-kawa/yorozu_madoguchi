import { useState } from 'react'
import { apiUrl } from '../utils/apiBase'
import type { PlanSummaryResponse } from '../types/api'

export const usePlan = (addSystemMessage: (text: string) => void) => {
  const [currentPlan, setCurrentPlan] = useState('')
  const [submittingPlan, setSubmittingPlan] = useState(false)

  const submitPlan = async () => {
    if (!currentPlan?.trim()) {
      return
    }

    setSubmittingPlan(true)
    try {
      const response = await fetch(apiUrl('/travel_submit_plan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: currentPlan }),
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Failed to submit plan')
      }

      let summary: PlanSummaryResponse | null = null
      try {
        const summaryResponse = await fetch(apiUrl('/complete'), {
          headers: { Accept: 'application/json' },
          credentials: 'include',
        })
        if (summaryResponse.ok) {
          summary = (await summaryResponse.json()) as PlanSummaryResponse
        }
      } catch (error) {
        console.warn("Failed to fetch summary:", error)
      }

      addSystemMessage('決定したプランを保存しました。')

      if (summary?.reservation_data?.length) {
        addSystemMessage(summary.reservation_data.join(' / '))
      }
    } catch (error) {
      console.error("SubmitPlan Error:", error)
      addSystemMessage('プランの保存に失敗しました。')
    } finally {
      setSubmittingPlan(false)
    }
  }

  return {
    currentPlan,
    setCurrentPlan,
    submittingPlan,
    submitPlan
  }
}
