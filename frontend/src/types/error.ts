export enum AppErrorType {
  Validation = 'validation_error',
  Session = 'session_error',
  Forbidden = 'forbidden',
  Unauthorized = 'unauthorized',
  Conflict = 'conflict',
  PayloadTooLarge = 'payload_too_large',
  RateLimit = 'rate_limit_exceeded',
  RedisUnavailable = 'redis_unavailable',
  Database = 'database_error',
  LlmTimeout = 'llm_timeout',
  LlmService = 'llm_service_error',
  ServiceUnavailable = 'service_unavailable',
  Network = 'network_error',
  Timeout = 'timeout_error',
  Unknown = 'unknown_error',
}

export type AppError = {
  type: AppErrorType
  message: string
  status?: number
  cause?: unknown
}

