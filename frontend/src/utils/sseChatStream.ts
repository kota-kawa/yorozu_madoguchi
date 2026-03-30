import type { ChatStreamEvent } from '../types/api'

/**
 * EN: Parse SSE payload blocks into a JSON object.
 * JP: SSEブロックをJSONオブジェクトへ変換する。
 */
const parseEventBlock = (block: string): ChatStreamEvent | null => {
  const lines = block.split('\n')
  const dataLines = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim())
  if (dataLines.length === 0) return null

  try {
    return JSON.parse(dataLines.join('\n')) as ChatStreamEvent
  } catch {
    return null
  }
}

/**
 * EN: Consume an SSE response body and dispatch parsed events.
 * JP: SSEレスポンス本文を読み取り、イベントをコールバックへ渡す。
 */
export const consumeChatSse = async (
  response: Response,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> => {
  if (!response.body) throw new Error('ストリーミング応答を取得できませんでした。')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''

    for (const block of blocks) {
      const event = parseEventBlock(block)
      if (event) {
        onEvent(event)
      }
    }
  }

  buffer += decoder.decode()
  if (buffer.trim()) {
    const event = parseEventBlock(buffer.trim())
    if (event) {
      onEvent(event)
    }
  }
}
