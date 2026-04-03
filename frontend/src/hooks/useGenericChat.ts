import { useEffect, useRef, useState } from 'react'
import { apiUrl } from '../utils/apiBase'
import { getStoredUserType } from '../utils/userType'
import { consumeChatSse } from '../utils/sseChatStream'
import { parseChatDirectiveText } from '../utils/chatDirectiveParser'
import type { ApiErrorResponse, ChatStreamFinalEvent } from '../types/api'
import type { ChatMessage, ChatMessageUpdate } from '../types/chat'
import type { AppError } from '../types/error'
import {
  makeClientValidationError,
  normalizeAppError,
  toFrontendAppError,
} from '../utils/errorHandling'

type UseGenericChatOptions = {
  initialMessage: ChatMessage
  messageEndpoint: string
  requestTimeoutMs?: number
  addSystemMessage?: boolean
  onError?: (error: AppError) => void
}

type PersistedChatState = {
  messages: ChatMessage[]
  planFromChat: string
}

const CHAT_STATE_STORAGE_PREFIX = 'yorozu_chat_state'

const buildChatStorageKey = (messageEndpoint: string): string =>
  `${CHAT_STATE_STORAGE_PREFIX}:${messageEndpoint.replace(/[^a-zA-Z0-9_-]/g, '_')}`

const getSessionStorage = (): Storage | null => {
  if (typeof window === 'undefined') return null
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

const isValidChatMessage = (value: unknown): value is ChatMessage => {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<ChatMessage>
  if (typeof candidate.id !== 'string') return false
  if (candidate.sender !== 'user' && candidate.sender !== 'bot') return false
  if (candidate.text !== undefined && typeof candidate.text !== 'string') return false
  if (
    candidate.type !== undefined &&
    candidate.type !== 'loading' &&
    candidate.type !== 'yesno' &&
    candidate.type !== 'selection' &&
    candidate.type !== 'date_selection'
  ) {
    return false
  }
  if (
    candidate.loading_variant !== undefined &&
    candidate.loading_variant !== 'thinking' &&
    candidate.loading_variant !== 'web_search'
  ) {
    return false
  }
  if (candidate.pending !== undefined && typeof candidate.pending !== 'boolean') return false
  if (
    candidate.choices !== undefined &&
    (!Array.isArray(candidate.choices) || candidate.choices.some((choice) => typeof choice !== 'string'))
  ) {
    return false
  }
  return true
}

const readPersistedChatState = (storageKey: string, initialMessage: ChatMessage): PersistedChatState => {
  const storage = getSessionStorage()
  if (!storage) {
    return { messages: [initialMessage], planFromChat: '' }
  }
  try {
    const raw = storage.getItem(storageKey)
    if (!raw) {
      return { messages: [initialMessage], planFromChat: '' }
    }
    const parsed = JSON.parse(raw) as Partial<PersistedChatState>
    const hydratedMessages = Array.isArray(parsed.messages)
      ? parsed.messages.filter(isValidChatMessage)
      : []
    return {
      messages: hydratedMessages.length > 0 ? hydratedMessages : [initialMessage],
      planFromChat: typeof parsed.planFromChat === 'string' ? parsed.planFromChat : '',
    }
  } catch {
    return { messages: [initialMessage], planFromChat: '' }
  }
}

const persistChatState = (storageKey: string, state: PersistedChatState): void => {
  const storage = getSessionStorage()
  if (!storage) return
  try {
    storage.setItem(storageKey, JSON.stringify(state))
  } catch {
    // Storage unavailable; keep in-memory only.
  }
}

export const clearAllPersistedChatStates = (): void => {
  const storage = getSessionStorage()
  if (!storage) return
  try {
    const keysToDelete: string[] = []
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index)
      if (typeof key === 'string' && key.startsWith(`${CHAT_STATE_STORAGE_PREFIX}:`)) {
        keysToDelete.push(key)
      }
    }
    keysToDelete.forEach((key) => storage.removeItem(key))
  } catch {
    // Storage unavailable; keep in-memory only.
  }
}

export type UseGenericChatResult = {
  messages: ChatMessage[]
  loading: boolean
  planFromChat: string
  sendMessage: (text: string) => Promise<void>
  addSystemMessage: (text: string) => void
  resetConversation: () => void
}

export const useGenericChat = ({
  initialMessage,
  messageEndpoint,
  requestTimeoutMs,
  addSystemMessage = false,
  onError,
}: UseGenericChatOptions): UseGenericChatResult => {
  const storageKey = buildChatStorageKey(messageEndpoint)
  const initialStateRef = useRef<PersistedChatState | null>(null)
  if (!initialStateRef.current) {
    initialStateRef.current = readPersistedChatState(storageKey, initialMessage)
  }
  const [messages, setMessages] = useState<ChatMessage[]>(initialStateRef.current.messages)
  const [loading, setLoading] = useState(false)
  const [planFromChat, setPlanFromChat] = useState(initialStateRef.current.planFromChat)
  const inFlightRef = useRef(false)

  useEffect(() => {
    persistChatState(storageKey, { messages, planFromChat })
  }, [storageKey, messages, planFromChat])

  const updateMessageText = (id: string, updater: string | ((prevText: string) => string)) => {
    setMessages((prev) =>
      prev.map((message) => {
        if (message.id !== id) return message
        const nextText = typeof updater === 'function' ? updater(message.text ?? '') : updater
        return { ...message, text: nextText }
      }),
    )
  }

  const updateMessageMeta = (id: string, updates: ChatMessageUpdate) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === id ? { ...message, ...updates } : message)),
    )
  }

  const finishSending = () => {
    inFlightRef.current = false
    setLoading(false)
  }

  const sendMessage = async (text: string) => {
    if (inFlightRef.current) return

    const trimmed = text.trim()
    if (!trimmed) return

    if (trimmed.length > 3000) {
      onError?.(
        normalizeAppError(
          makeClientValidationError(
            '入力された文字数が3000文字を超えています。3000文字以内で入力してください。',
          ),
        ),
      )
      return
    }

    inFlightRef.current = true

    const userMessage: ChatMessage = { id: `user-${Date.now()}`, sender: 'user', text: trimmed }
    const loadingMessageId = `bot-${Date.now()}`
    const loadingMessage: ChatMessage = {
      id: loadingMessageId,
      sender: 'bot',
      text: '考えています',
      type: 'loading',
      loading_variant: 'thinking',
      pending: true,
    }

    setMessages((prev) => [...prev, userMessage, loadingMessage])
    setLoading(true)

    const requestController = new AbortController()
    const timeoutId =
      typeof requestTimeoutMs === 'number' && requestTimeoutMs > 0
        ? setTimeout(() => requestController.abort(), requestTimeoutMs)
        : null

    try {
      const response = await fetch(apiUrl(messageEndpoint), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ message: trimmed, user_type: getStoredUserType(), stream: true }),
        credentials: 'include',
        signal: requestController.signal,
      })

      const contentType = response.headers.get('content-type') || ''
      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as ApiErrorResponse | null
        throw toFrontendAppError(data, response.status)
      }
      if (!contentType.includes('text/event-stream')) {
        throw makeClientValidationError('ストリーミング応答の受信に失敗しました。')
      }

      let streamedRawText = ''
      const streamState: { finalEvent: ChatStreamFinalEvent | null; usedWebSearch: boolean } = {
        finalEvent: null,
        usedWebSearch: false,
      }

      updateMessageMeta(loadingMessageId, {
        type: 'loading',
        loading_variant: 'thinking',
        pending: false,
      })

      const directiveState: {
        yesNoPhrase: string | null
        choices: string[]
        isDateSelect: boolean
      } = {
        yesNoPhrase: null,
        choices: [],
        isDateSelect: false,
      }
      const applyDirectiveToMessage = (id: string, rawText: string): string => {
        const parsed = parseChatDirectiveText(rawText)
        directiveState.yesNoPhrase = parsed.yesNoPhrase
        directiveState.choices = parsed.choices
        directiveState.isDateSelect = parsed.isDateSelect

        const messageType =
          directiveState.choices.length > 0
            ? 'selection'
            : directiveState.yesNoPhrase
              ? 'yesno'
              : directiveState.isDateSelect
                ? 'date_selection'
                : 'loading'

        updateMessageMeta(id, {
          type: messageType,
          loading_variant: messageType === 'loading' ? (streamState.usedWebSearch ? 'web_search' : 'thinking') : undefined,
          pending: false,
          choices: directiveState.choices.length > 0 ? directiveState.choices : undefined,
        })

        if (directiveState.yesNoPhrase) {
          return directiveState.yesNoPhrase
        }
        return parsed.cleanedText
      }

      await consumeChatSse(response, (event) => {
        if (event.type === 'meta') {
          streamState.usedWebSearch = Boolean(event.used_web_search)
          updateMessageMeta(loadingMessageId, {
            loading_variant: streamState.usedWebSearch ? 'web_search' : 'thinking',
          })
          return
        }
        if (event.type === 'delta') {
          if (typeof event.content === 'string' && event.content) {
            streamedRawText += event.content
            updateMessageText(loadingMessageId, () => applyDirectiveToMessage(loadingMessageId, streamedRawText))
          }
          return
        }
        if (event.type === 'final') {
          streamState.finalEvent = event
        }
      })

      if (!streamState.finalEvent) {
        throw new Error('ストリーミングが途中で終了しました。')
      }
      const finalResult = streamState.finalEvent

      if (finalResult.current_plan !== undefined) {
        setPlanFromChat(finalResult.current_plan ?? '')
      }

      const remainingText = finalResult.remaining_text
      const remainingTextValue =
        typeof remainingText === 'string' && remainingText !== 'Empty' ? remainingText : null
      const finalText = remainingTextValue ?? finalResult.response ?? ''
      const parsedFinalText = parseChatDirectiveText(finalText)
      const finalChoices =
        finalResult.choices && Array.isArray(finalResult.choices) && finalResult.choices.length > 0
          ? finalResult.choices
          : directiveState.choices.length > 0
            ? directiveState.choices
            : parsedFinalText.choices
      const finalYesNoPhrase =
        finalResult.yes_no_phrase ?? directiveState.yesNoPhrase ?? parsedFinalText.yesNoPhrase
      const finalIsDateSelect = Boolean(
        finalResult.is_date_select || directiveState.isDateSelect || parsedFinalText.isDateSelect,
      )
      const finalMessageType =
        finalChoices.length > 0 ? 'selection' : finalYesNoPhrase ? 'yesno' : finalIsDateSelect ? 'date_selection' : undefined
      const finalMessageText = finalYesNoPhrase ?? parsedFinalText.cleanedText

      updateMessageMeta(loadingMessageId, {
        text: finalMessageText,
        type: finalMessageType,
        loading_variant: undefined,
        pending: false,
        choices: finalChoices.length > 0 ? finalChoices : undefined,
      })

      finishSending()
    } catch (error) {
      const appError = normalizeAppError(error)
      const message = appError.message

      setMessages((prev) =>
        prev
          .filter((messageItem) => messageItem.id !== loadingMessageId)
          .concat({ id: `error-${Date.now()}`, sender: 'bot', text: message }),
      )
      onError?.(appError)
      finishSending()
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }

  const addSystemMessageFn = (text: string) => {
    setMessages((prev) => [...prev, { id: `sys-${Date.now()}`, sender: 'bot', text }])
  }

  const resetConversation = () => {
    const nextMessages = [{ ...initialMessage }]
    inFlightRef.current = false
    setLoading(false)
    setMessages(nextMessages)
    setPlanFromChat('')
    persistChatState(storageKey, { messages: nextMessages, planFromChat: '' })
  }

  return {
    messages,
    loading,
    planFromChat,
    sendMessage,
    addSystemMessage: addSystemMessage ? addSystemMessageFn : () => {},
    resetConversation,
  }
}
