/**
 * EN: Provide the streamHelper module implementation.
 * JP: streamHelper モジュールの実装を定義する。
 */
import type { WorkerInputMessage, WorkerOutputMessage } from '../types/worker'

/**
 * EN: Declare the streamWithWorker value.
 * JP: streamWithWorker の値を宣言する。
 */
export const streamWithWorker = (
  worker: Worker,
  text: string,
  onChunk: (chunk: string) => void,
  onDone: () => void,
): void => {
  let isCompleted = false

  /**
   * EN: Declare the finalize value.
   * JP: finalize の値を宣言する。
   */
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
