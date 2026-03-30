/**
 * EN: Define the ChatApiResponse type alias.
 * JP: ChatApiResponse 型エイリアスを定義する。
 */
/**
 * EN: Provide the api module implementation.
 * JP: api モジュールの実装を定義する。
 */
/**
 * EN: Define shared chat response payload fields.
 * JP: チャット応答の共通ペイロード項目を定義する。
 */
export type ChatResponsePayload = {
  response?: string | null
  remaining_text?: string | null
  yes_no_phrase?: string | null
  choices?: string[] | null
  is_date_select?: boolean
  current_plan?: string | null
}

export type ChatApiResponse = ChatResponsePayload & {
  used_web_search?: boolean
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

export type ChatStreamFinalEvent = ChatResponsePayload & {
  type: 'final'
  used_web_search?: boolean
}

export type ChatStreamEvent = ChatStreamMetaEvent | ChatStreamDeltaEvent | ChatStreamFinalEvent

/**
 * EN: Define the PlanSummaryResponse type alias.
 * JP: PlanSummaryResponse 型エイリアスを定義する。
 */
export type PlanSummaryResponse = {
  reservation_data?: string[]
}
