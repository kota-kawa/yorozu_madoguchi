export type ChatSender = 'user' | 'bot'

export type ChatMessageType = 'loading' | 'yesno' | 'selection' | 'date_selection'

export type ChatMessage = {
  id: string
  sender: ChatSender
  text?: string
  type?: ChatMessageType
  pending?: boolean
  choices?: string[]
}

export type ChatMessageUpdate = Partial<ChatMessage>
