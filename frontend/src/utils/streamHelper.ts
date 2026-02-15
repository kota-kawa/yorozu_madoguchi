import type { WorkerInputMessage, WorkerOutputMessage } from '../types/worker'

export const streamWithWorker = (
  worker: Worker,
  text: string,
  onChunk: (chunk: string) => void,
  onDone: () => void,
): void => {
  let isCompleted = false

  const finalize = () => {
    if (isCompleted) return
    isCompleted = true
    onDone()
  }

  worker.onmessage = (event: MessageEvent<WorkerOutputMessage>) => {
    if (event.data?.type === 'text') {
      onChunk(event.data.content)
      return
    }

    if (event.data?.type === 'done') {
      finalize()
    }
  }
  worker.onerror = () => finalize()
  worker.onmessageerror = () => finalize()
  worker.postMessage({ remaining_text: text } as WorkerInputMessage)
}
