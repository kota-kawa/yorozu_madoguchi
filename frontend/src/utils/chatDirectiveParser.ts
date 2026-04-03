export type ParsedChatDirective = {
  cleanedText: string
  yesNoPhrase: string | null
  choices: string[]
  isDateSelect: boolean
}

const SELECT_PATTERN = /(?:^|\n)\s*Select\s*[:：]\s*(?:\[|［)([\s\S]*?)(?:\]|］)\s*/i
const DATE_SELECT_PATTERN = /(?:^|\n)\s*DateSelect\s*[:：]\s*true\s*/i
const YES_NO_PATTERN = /(?:^|\n)\s*Yes\/No\s*[:：]\s*([^\n]*?[?？])\s*/i

const normalizeText = (text: string): string =>
  text
    .split('\n')
    .map((line) => line.trimEnd())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

const extractChoices = (rawChoices: string): string[] =>
  rawChoices
    .split(/[,、，]/)
    .map((choice) => choice.trim().replace(/^[-*]\s*/, '').replace(/^["']|["']$/g, ''))
    .filter((choice) => choice.length > 0)

export const parseChatDirectiveText = (rawText: string): ParsedChatDirective => {
  const normalized = typeof rawText === 'string' ? rawText : ''
  let workingText = normalized

  const selectMatch = workingText.match(SELECT_PATTERN)
  if (selectMatch) {
    const choices = extractChoices(selectMatch[1] ?? '')
    workingText = workingText.replace(selectMatch[0], '\n')
    return {
      cleanedText: normalizeText(workingText),
      yesNoPhrase: null,
      choices,
      isDateSelect: false,
    }
  }

  const dateSelectMatch = workingText.match(DATE_SELECT_PATTERN)
  if (dateSelectMatch) {
    workingText = workingText.replace(dateSelectMatch[0], '\n')
    return {
      cleanedText: normalizeText(workingText),
      yesNoPhrase: null,
      choices: [],
      isDateSelect: true,
    }
  }

  const yesNoMatch = workingText.match(YES_NO_PATTERN)
  if (yesNoMatch) {
    workingText = workingText.replace(yesNoMatch[0], '\n')
    return {
      cleanedText: normalizeText(workingText),
      yesNoPhrase: (yesNoMatch[1] ?? '').trim() || null,
      choices: [],
      isDateSelect: false,
    }
  }

  return {
    cleanedText: normalizeText(workingText),
    yesNoPhrase: null,
    choices: [],
    isDateSelect: false,
  }
}
