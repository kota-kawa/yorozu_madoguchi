/**
 * EN: Define the ChatApiResponse type alias.
 * JP: ChatApiResponse 型エイリアスを定義する。
 */
/**
 * EN: Provide the api module implementation.
 * JP: api モジュールの実装を定義する。
 */
export type ChatApiResponse = {
  response?: string
  remaining_text?: string | null
  yes_no_phrase?: string
  choices?: string[] | null
  is_date_select?: boolean
  current_plan?: string | null
  error?: string
}

/**
 * EN: Define the PlanSummaryResponse type alias.
 * JP: PlanSummaryResponse 型エイリアスを定義する。
 */
export type PlanSummaryResponse = {
  reservation_data?: string[]
}
