import type { ChatMessage } from '../types/chat'
import { useGenericChat } from './useGenericChat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text:
    '自己PR・ES・志望動機・面接対策のうち、今取り組みたい内容を教えてください。企業や職種、文字数、設問文があれば一緒にお願いします。',
}

export const useJobChat = () =>
  useGenericChat({
    initialMessage,
    messageEndpoint: '/job_send_message',
  })
