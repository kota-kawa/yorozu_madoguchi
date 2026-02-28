import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  getStoredUserType,
  normalizeUserType,
  setStoredUserType,
  userTypeKey,
} from './userType'

describe('userType utils', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.restoreAllMocks()
  })

  it('normalizes supported user types', () => {
    expect(normalizeUserType(' normal ')).toBe('normal')
    expect(normalizeUserType('PREMIUM')).toBe('premium')
  })

  it('returns empty string for unsupported user types', () => {
    expect(normalizeUserType('guest')).toBe('')
    expect(normalizeUserType('')).toBe('')
    expect(normalizeUserType(null)).toBe('')
    expect(normalizeUserType(undefined)).toBe('')
  })

  it('stores and loads user type from localStorage', () => {
    setStoredUserType('premium')
    expect(window.localStorage.getItem(userTypeKey)).toBe('premium')
    expect(getStoredUserType()).toBe('premium')
  })

  it('returns empty string when localStorage getItem throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable')
    })

    expect(getStoredUserType()).toBe('')
  })

  it('does not throw when localStorage setItem throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage unavailable')
    })

    expect(() => setStoredUserType('normal')).not.toThrow()
  })
})
