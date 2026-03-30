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
  used_web_search?: boolean
  current_plan?: string | null
  error?: string
}

export type ChatStreamMetaEvent = {
  type: 'meta'
  used_web_search?: boolean
}

export type ChatStreamDeltaEvent = {
  type: 'delta'
  content?: string
}

export type ChatStreamFinalEvent = {
  type: 'final'
  response?: string | null
  remaining_text?: string | null
  yes_no_phrase?: string | null
  choices?: string[] | null
  is_date_select?: boolean
  used_web_search?: boolean
  current_plan?: string | null
}

export type ChatStreamEvent = ChatStreamMetaEvent | ChatStreamDeltaEvent | ChatStreamFinalEvent

/**
 * EN: Define the PlanSummaryResponse type alias.
 * JP: PlanSummaryResponse 型エイリアスを定義する。
 */
export type PlanSummaryResponse = {
  reservation_data?: string[]
}
