export type ChatApiResponse = {
  response?: string
  remaining_text?: string | null
  yes_no_phrase?: string
  choices?: string[] | null
  is_date_select?: boolean
  current_plan?: string | null
  error?: string
}

export type PlanSummaryResponse = {
  reservation_data?: string[]
}
