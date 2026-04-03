import { describe, expect, it } from 'vitest'

import { parseChatDirectiveText } from './chatDirectiveParser'

describe('parseChatDirectiveText', () => {
  it('extracts selection choices and removes directive from text', () => {
    const parsed = parseChatDirectiveText(
      'どのタイプが近いですか？\nSelect: [筋肥大, 減量, 姿勢改善, その他]',
    )

    expect(parsed.cleanedText).toBe('どのタイプが近いですか？')
    expect(parsed.choices).toEqual(['筋肥大', '減量', '姿勢改善', 'その他'])
    expect(parsed.yesNoPhrase).toBeNull()
    expect(parsed.isDateSelect).toBe(false)
  })

  it('extracts yes/no phrase and keeps guide text', () => {
    const parsed = parseChatDirectiveText('まずは方向性を確認します。\nYes/No: この条件で進めますか？')

    expect(parsed.cleanedText).toBe('まずは方向性を確認します。')
    expect(parsed.yesNoPhrase).toBe('この条件で進めますか？')
    expect(parsed.choices).toEqual([])
    expect(parsed.isDateSelect).toBe(false)
  })

  it('extracts date selection directive', () => {
    const parsed = parseChatDirectiveText('都合のよい日付を選んでください。\nDateSelect: true')

    expect(parsed.cleanedText).toBe('都合のよい日付を選んでください。')
    expect(parsed.isDateSelect).toBe(true)
    expect(parsed.choices).toEqual([])
    expect(parsed.yesNoPhrase).toBeNull()
  })
})
