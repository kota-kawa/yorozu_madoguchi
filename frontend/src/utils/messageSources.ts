export type SourceLanguage = 'ja' | 'en'

export type SplitMessageSourcesResult = {
  bodyText: string
  sourceUrls: string[]
  sourceLanguage: SourceLanguage | null
}

const SOURCE_SECTION_PATTERN =
  /(?:^|\n)(参考URL|Sources):\s*\n((?:\s*-\s*https?:\/\/[^\s]+(?:\n|$))+)\s*$/u

const URL_PATTERN = /https?:\/\/[^\s)>\]}]+/i

const extractUrl = (line: string): string | null => {
  const normalized = line.replace(/^\s*-\s*/, '').trim()
  const match = normalized.match(URL_PATTERN)
  return match ? match[0] : null
}

export const splitMessageSources = (rawText: string): SplitMessageSourcesResult => {
  const normalizedText = rawText.replace(/\r\n/g, '\n')
  const match = normalizedText.match(SOURCE_SECTION_PATTERN)
  if (!match || typeof match.index !== 'number') {
    return { bodyText: rawText, sourceUrls: [], sourceLanguage: null }
  }

  const sourceUrls: string[] = []
  const sourceLines = match[2].split('\n').map((line) => line.trim()).filter(Boolean)
  sourceLines.forEach((line) => {
    const url = extractUrl(line)
    if (!url || sourceUrls.includes(url)) return
    sourceUrls.push(url)
  })

  if (sourceUrls.length === 0) {
    return { bodyText: rawText, sourceUrls: [], sourceLanguage: null }
  }

  const bodyText = normalizedText.slice(0, match.index).trimEnd()
  return {
    bodyText,
    sourceUrls,
    sourceLanguage: match[1] === 'Sources' ? 'en' : 'ja',
  }
}
