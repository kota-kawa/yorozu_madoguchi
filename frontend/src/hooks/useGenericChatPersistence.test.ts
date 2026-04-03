import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearAllPersistedChatStates } from './useGenericChat'

describe('useGenericChat persistence helpers', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('clears only chat persistence entries', () => {
    window.sessionStorage.setItem('yorozu_chat_state:_travel_send_message', '{"messages":[],"planFromChat":""}')
    window.sessionStorage.setItem('yorozu_chat_state:_reply_send_message', '{"messages":[],"planFromChat":""}')
    window.sessionStorage.setItem('unrelated_key', 'keep')

    clearAllPersistedChatStates()

    expect(window.sessionStorage.getItem('yorozu_chat_state:_travel_send_message')).toBeNull()
    expect(window.sessionStorage.getItem('yorozu_chat_state:_reply_send_message')).toBeNull()
    expect(window.sessionStorage.getItem('unrelated_key')).toBe('keep')
  })

  it('does not throw when storage access fails', () => {
    vi.spyOn(window.sessionStorage, 'key').mockImplementation(() => {
      throw new Error('storage unavailable')
    })

    expect(() => clearAllPersistedChatStates()).not.toThrow()
  })
})
