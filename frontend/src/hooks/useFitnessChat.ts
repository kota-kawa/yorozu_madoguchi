import type { ChatMessage } from '../types/chat'
import { useGenericChat } from './useGenericChat'

const initialMessage: ChatMessage = {
  id: 'welcome',
  sender: 'bot',
  text: '目的（筋肥大・減量・健康維持など）と、今の運動頻度や使える器具を教えてください。',
}

export const useFitnessChat = () =>
  useGenericChat({
    initialMessage,
    messageEndpoint: '/fitness_send_message',
  })
