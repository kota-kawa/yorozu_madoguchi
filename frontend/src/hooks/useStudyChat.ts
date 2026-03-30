import type { ChatMessage } from '../types/chat'
import { useGenericChat } from './useGenericChat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text:
    '今日の授業メモや教材の内容を送ってください。整理ノートや要点サマリー、用語集、確認問題を作成します。',
}

export const useStudyChat = () =>
  useGenericChat({
    initialMessage,
    messageEndpoint: '/study_send_message',
  })
