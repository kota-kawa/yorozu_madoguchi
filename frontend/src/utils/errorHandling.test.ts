import { describe, expect, it } from 'vitest'

import { AppErrorType } from '../types/error'
import {
  FrontendAppError,
  normalizeAppError,
  toFrontendAppError,
} from './errorHandling'

describe('errorHandling utils', () => {
  it('maps backend error type and message into FrontendAppError', () => {
    const error = toFrontendAppError(
      {
        error: 'backend error',
        response: '利用状況を確認できません。しばらく待ってから再試行してください。',
        error_type: 'redis_unavailable',
      },
      503,
    )

    expect(error).toBeInstanceOf(FrontendAppError)
    expect(error.type).toBe(AppErrorType.RedisUnavailable)
    expect(error.message).toBe('利用状況を確認できません。しばらく待ってから再試行してください。')
    expect(error.status).toBe(503)
  })

  it('falls back to status-based type when explicit type is missing', () => {
    const error = toFrontendAppError({ error: 'too many requests' }, 429)

    expect(error.type).toBe(AppErrorType.RateLimit)
    expect(error.message).toBe('too many requests')
  })

  it('normalizes AbortError as timeout', () => {
    const abortError = new DOMException('Request aborted', 'AbortError')
    const normalized = normalizeAppError(abortError)

    expect(normalized.type).toBe(AppErrorType.Timeout)
    expect(normalized.message).toBe('サーバーからの応答がありません。もう一度お試しください。')
  })
})

