import type { WorkerInputMessage, WorkerOutputMessage } from '../types/worker'

export const streamWithWorker = (
  worker: Worker,
  text: string,
  onChunk: (chunk: string) => void,
  onDone: () => void,
): void => {
  worker.onmessage = (event: MessageEvent<WorkerOutputMessage>) => {
    if (event.data?.type === 'text') {
      onChunk(event.data.content)
      return
    }

    if (event.data?.type === 'done') {
      onDone()
    }
  }
  worker.postMessage({ remaining_text: text } as WorkerInputMessage)
}
