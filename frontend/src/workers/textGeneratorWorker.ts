/// <reference lib="webworker" />

import type { WorkerInputMessage, WorkerOutputMessage } from '../types/worker'

const ctx = self as DedicatedWorkerGlobalScope

ctx.onmessage = (event: MessageEvent<WorkerInputMessage>) => {
  const remainingText = event.data?.remaining_text || ''
  let index = 0

  // 以前の40msから15msに短縮し、よりスムーズに表示されるようにする
  const interval = setInterval(() => {
    if (index < remainingText.length) {
      // 処理落ちを防ぐため、長いテキストの場合は一度に送る文字数を少し増やすなどの調整も考えられるが
      // まずは単純に頻度を上げる
      ctx.postMessage({ type: 'text', content: remainingText.charAt(index) } as WorkerOutputMessage)
      index += 1
      return
    }

    clearInterval(interval)
    ctx.postMessage({ type: 'done' } as WorkerOutputMessage)
  }, 15)
}

export {}
