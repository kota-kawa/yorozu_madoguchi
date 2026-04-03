import { describe, expect, it } from 'vitest'

import { splitMessageSources } from './messageSources'

describe('splitMessageSources', () => {
  it('splits Japanese source section into body and urls', () => {
    const parsed = splitMessageSources(
      '最新の情報です。\n\n参考URL:\n- https://example.com/a\n- https://example.com/b',
    )

    expect(parsed.bodyText).toBe('最新の情報です。')
    expect(parsed.sourceUrls).toEqual(['https://example.com/a', 'https://example.com/b'])
    expect(parsed.sourceLanguage).toBe('ja')
  })

  it('supports English source header and deduplicates URLs', () => {
    const parsed = splitMessageSources(
      'Here is an answer.\n\nSources:\n- https://example.com/a\n- https://example.com/a',
    )

    expect(parsed.bodyText).toBe('Here is an answer.')
    expect(parsed.sourceUrls).toEqual(['https://example.com/a'])
    expect(parsed.sourceLanguage).toBe('en')
  })

  it('returns original text when source section does not exist', () => {
    const raw = 'リンクっぽい文字列 https://example.com が文中にあるだけ'
    const parsed = splitMessageSources(raw)

    expect(parsed.bodyText).toBe(raw)
    expect(parsed.sourceUrls).toEqual([])
    expect(parsed.sourceLanguage).toBeNull()
  })
})
