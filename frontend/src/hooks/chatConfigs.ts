import type { ChatMessage } from '../types/chat'
import type { AppError } from '../types/error'

type ChatConfig = {
  initialMessage: ChatMessage
  messageEndpoint: string
  requestTimeoutMs?: number
  addSystemMessage?: boolean
  onError?: (error: AppError) => void
}

export type ChatFeature = 'travel' | 'reply' | 'fitness' | 'job' | 'study'

export const CHAT_CONFIGS: Record<ChatFeature, ChatConfig> = {
  travel: {
    initialMessage: {
      id: 'welcome',
      sender: 'bot',
      text: 'どんな旅行の計画を一緒に立てますか？😊',
    },
    messageEndpoint: '/travel_send_message',
    addSystemMessage: true,
  },
  reply: {
    initialMessage: {
      id: 'welcome',
      sender: 'bot',
      text: '返信したいLINEやDMの内容と、どのようなことをしたいか・言いたいかを教えてください。\nより多くの会話履歴が示されると良い答えを考えやすいです！',
    },
    messageEndpoint: '/reply_send_message',
    requestTimeoutMs: 60000,
  },
  fitness: {
    initialMessage: {
      id: 'welcome',
      sender: 'bot',
      text: '目的（筋肥大・減量・健康維持など）と、今の運動頻度や使える器具を教えてください。',
    },
    messageEndpoint: '/fitness_send_message',
  },
  job: {
    initialMessage: {
      id: 'welcome',
      sender: 'bot',
      text: '自己PR・ES・志望動機・面接対策のうち、今取り組みたい内容を教えてください。企業や職種、文字数、設問文があれば一緒にお願いします。',
    },
    messageEndpoint: '/job_send_message',
  },
  study: {
    initialMessage: {
      id: 'welcome',
      sender: 'bot',
      text: '今日の授業メモや教材の内容を送ってください。整理ノートや要点サマリー、用語集、確認問題を作成します。',
    },
    messageEndpoint: '/study_send_message',
  },
}
