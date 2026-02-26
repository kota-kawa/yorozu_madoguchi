/**
 * EN: Define the ChatSender type alias.
 * JP: ChatSender 型エイリアスを定義する。
 */
/**
 * EN: Provide the chat module implementation.
 * JP: chat モジュールの実装を定義する。
 */
export type ChatSender = 'user' | 'bot'

/**
 * EN: Define the ChatMessageType type alias.
 * JP: ChatMessageType 型エイリアスを定義する。
 */
export type ChatMessageType = 'loading' | 'yesno' | 'selection' | 'date_selection'

/**
 * EN: Define the ChatMessage type alias.
 * JP: ChatMessage 型エイリアスを定義する。
 */
export type ChatMessage = {
  id: string
  sender: ChatSender
  text?: string
  type?: ChatMessageType
  pending?: boolean
  choices?: string[]
}

/**
 * EN: Define the ChatMessageUpdate type alias.
 * JP: ChatMessageUpdate 型エイリアスを定義する。
 */
export type ChatMessageUpdate = Partial<ChatMessage>
