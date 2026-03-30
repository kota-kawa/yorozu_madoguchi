/**
 * EN: Provide the useReplyChat module implementation.
 * JP: useReplyChat モジュールの実装を定義する。
 */
import type { ChatMessage } from '../types/chat'
import { useGenericChat } from './useGenericChat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text: '返信したいLINEやDMの内容と、どのようなことをしたいか・言いたいかを教えてください。\nより多くの会話履歴が示されると良い答えを考えやすいです！',
}

/**
 * EN: Declare the useReplyChat value.
 * JP: useReplyChat の値を宣言する。
 */
export const useReplyChat = () =>
  useGenericChat({
    initialMessage,
    messageEndpoint: '/reply_send_message',
    requestTimeoutMs: 60000,
  })
