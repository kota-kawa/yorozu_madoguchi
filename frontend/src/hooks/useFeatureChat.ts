import { CHAT_CONFIGS } from './chatConfigs'
import type { ChatFeature } from './chatConfigs'
import { useGenericChat } from './useGenericChat'
import type { UseGenericChatResult } from './useGenericChat'
import type { AppError } from '../types/error'

export const useFeatureChat = (
  feature: ChatFeature,
  options?: {
    onError?: (error: AppError) => void
  },
): UseGenericChatResult => {
  const config = CHAT_CONFIGS[feature]
  return useGenericChat({
    ...config,
    onError: options?.onError ?? config.onError,
  })
}
