/**
 * EN: Provide the useChat module implementation.
 * JP: useChat モジュールの実装を定義する。
 */
import type { ChatMessage } from '../types/chat'
import { useGenericChat } from './useGenericChat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text: 'どんな旅行の計画を一緒に立てますか？😊',
}

/**
 * EN: Declare the useChat value.
 * JP: useChat の値を宣言する。
 */
export const useChat = () =>
  useGenericChat({
    initialMessage,
    messageEndpoint: '/travel_send_message',
    addSystemMessage: true,
  })
