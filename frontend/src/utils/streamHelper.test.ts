import { describe, expect, it, vi } from 'vitest'

import { streamWithWorker } from './streamHelper'

type MockWorker = {
  onmessage: ((event: MessageEvent<unknown>) => void) | null
  onerror: ((event: ErrorEvent) => void) | null
  onmessageerror: ((event: MessageEvent<unknown>) => void) | null
  postMessage: ReturnType<typeof vi.fn>
}

const createMockWorker = (): MockWorker => ({
  onmessage: null,
  onerror: null,
  onmessageerror: null,
  postMessage: vi.fn(),
})

describe('streamWithWorker', () => {
  it('posts initial payload, streams text chunks, and finalizes once', () => {
    const worker = createMockWorker()
    const onChunk = vi.fn()
    const onDone = vi.fn()

    streamWithWorker(worker as unknown as Worker, 'remaining', onChunk, onDone)

    expect(worker.postMessage).toHaveBeenCalledWith({ remaining_text: 'remaining' })

    worker.onmessage?.({
      data: { type: 'text', content: 'chunk-1' },
    } as MessageEvent<unknown>)
    expect(onChunk).toHaveBeenCalledWith('chunk-1')
    expect(onDone).not.toHaveBeenCalled()

    worker.onmessage?.({
      data: { type: 'done' },
    } as MessageEvent<unknown>)
    expect(onDone).toHaveBeenCalledTimes(1)

    worker.onmessage?.({
      data: { type: 'done' },
    } as MessageEvent<unknown>)
    worker.onerror?.({} as ErrorEvent)
    worker.onmessageerror?.({} as MessageEvent<unknown>)
    expect(onDone).toHaveBeenCalledTimes(1)
  })

  it('finalizes when worker emits error before done', () => {
    const worker = createMockWorker()
    const onChunk = vi.fn()
    const onDone = vi.fn()

    streamWithWorker(worker as unknown as Worker, 'remaining', onChunk, onDone)
    worker.onerror?.({} as ErrorEvent)

    expect(onDone).toHaveBeenCalledTimes(1)
    expect(onChunk).not.toHaveBeenCalled()
  })
})
