import { CHAT_CONFIGS } from './chatConfigs'
import type { ChatFeature } from './chatConfigs'
import { useGenericChat } from './useGenericChat'
import type { UseGenericChatResult } from './useGenericChat'

export const useFeatureChat = (feature: ChatFeature): UseGenericChatResult => {
  const config = CHAT_CONFIGS[feature]
  return useGenericChat(config)
}
