import type { ApiErrorResponse } from '../types/api'
import { AppErrorType, type AppError } from '../types/error'

const FALLBACK_ERROR_MESSAGE = 'サーバーからの応答に失敗しました。時間をおいて再試行してください。'
const TIMEOUT_ERROR_MESSAGE = 'サーバーからの応答がありません。もう一度お試しください。'

const normalizeErrorType = (value: string | undefined | null): AppErrorType => {
  switch (value) {
    case AppErrorType.Validation:
      return AppErrorType.Validation
    case AppErrorType.Session:
      return AppErrorType.Session
    case AppErrorType.Forbidden:
      return AppErrorType.Forbidden
    case AppErrorType.Unauthorized:
      return AppErrorType.Unauthorized
    case AppErrorType.Conflict:
      return AppErrorType.Conflict
    case AppErrorType.PayloadTooLarge:
      return AppErrorType.PayloadTooLarge
    case AppErrorType.RateLimit:
      return AppErrorType.RateLimit
    case AppErrorType.RedisUnavailable:
      return AppErrorType.RedisUnavailable
    case AppErrorType.Database:
      return AppErrorType.Database
    case AppErrorType.LlmTimeout:
      return AppErrorType.LlmTimeout
    case AppErrorType.LlmService:
      return AppErrorType.LlmService
    case AppErrorType.ServiceUnavailable:
      return AppErrorType.ServiceUnavailable
    default:
      return AppErrorType.Unknown
  }
}

const defaultMessageByType = (type: AppErrorType): string => {
  switch (type) {
    case AppErrorType.Validation:
      return '入力内容に誤りがあります。内容を確認して再試行してください。'
    case AppErrorType.Session:
      return 'セッションが無効です。ページを再読み込みしてお試しください。'
    case AppErrorType.Forbidden:
      return '不正なリクエストです。ページを再読み込みしてお試しください。'
    case AppErrorType.Conflict:
      return '前の処理が完了していません。少し待って再試行してください。'
    case AppErrorType.PayloadTooLarge:
      return '送信データが大きすぎます。入力内容を短くして再試行してください。'
    case AppErrorType.RateLimit:
      return '利用上限に達しました。時間をおいて再試行してください。'
    case AppErrorType.RedisUnavailable:
    case AppErrorType.Database:
    case AppErrorType.ServiceUnavailable:
      return '現在システムが混み合っています。しばらくしてから再試行してください。'
    case AppErrorType.LlmTimeout:
    case AppErrorType.Timeout:
      return TIMEOUT_ERROR_MESSAGE
    case AppErrorType.LlmService:
      return '応答生成サービスで一時的なエラーが発生しました。しばらく待って再試行してください。'
    default:
      return FALLBACK_ERROR_MESSAGE
  }
}

const sanitizeMessage = (value: unknown): string => {
  if (typeof value !== 'string') return ''
  const trimmed = value.trim()
  if (!trimmed || trimmed === 'Failed to fetch') return ''
  return trimmed
}

const inferTypeFromStatus = (status?: number): AppErrorType => {
  if (status === 400) return AppErrorType.Validation
  if (status === 401) return AppErrorType.Unauthorized
  if (status === 403) return AppErrorType.Forbidden
  if (status === 409) return AppErrorType.Conflict
  if (status === 413) return AppErrorType.PayloadTooLarge
  if (status === 429) return AppErrorType.RateLimit
  if (status === 503) return AppErrorType.ServiceUnavailable
  if (status === 504) return AppErrorType.Timeout
  return AppErrorType.Unknown
}

export class FrontendAppError extends Error {
  type: AppErrorType
  status?: number
  cause?: unknown

  constructor(appError: AppError) {
    super(appError.message)
    this.name = 'FrontendAppError'
    this.type = appError.type
    this.status = appError.status
    this.cause = appError.cause
  }
}

export const normalizeAppError = (error: unknown): AppError => {
  if (error instanceof FrontendAppError) {
    return {
      type: error.type,
      message: error.message,
      status: error.status,
      cause: error.cause,
    }
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return {
      type: AppErrorType.Timeout,
      message: TIMEOUT_ERROR_MESSAGE,
      cause: error,
    }
  }
  if (error instanceof TypeError && /Failed to fetch/i.test(error.message)) {
    return {
      type: AppErrorType.Network,
      message: 'ネットワーク接続を確認して再試行してください。',
      cause: error,
    }
  }
  if (error instanceof Error) {
    const message = sanitizeMessage(error.message) || FALLBACK_ERROR_MESSAGE
    return { type: AppErrorType.Unknown, message, cause: error }
  }
  return { type: AppErrorType.Unknown, message: FALLBACK_ERROR_MESSAGE, cause: error }
}

export const toFrontendAppError = (
  payload: ApiErrorResponse | null,
  status: number,
  fallbackMessage: string = FALLBACK_ERROR_MESSAGE,
): FrontendAppError => {
  const explicitType = normalizeErrorType(payload?.error_type || payload?.error_code)
  const inferredType = inferTypeFromStatus(status)
  const type = explicitType !== AppErrorType.Unknown ? explicitType : inferredType
  const message = sanitizeMessage(payload?.response) || sanitizeMessage(payload?.error) || fallbackMessage
  return new FrontendAppError({
    type,
    message: message || defaultMessageByType(type),
    status,
    cause: payload,
  })
}

export const makeClientValidationError = (message: string): FrontendAppError =>
  new FrontendAppError({
    type: AppErrorType.Validation,
    message,
  })

export const makeClientUnsupportedError = (message: string): FrontendAppError =>
  new FrontendAppError({
    type: AppErrorType.Validation,
    message,
  })

export const getUserFacingMessage = (error: unknown): string => {
  const normalized = normalizeAppError(error)
  return normalized.message || defaultMessageByType(normalized.type)
}
