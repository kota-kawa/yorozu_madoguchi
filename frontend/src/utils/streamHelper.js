export const streamWithWorker = (worker, text, onChunk, onDone) => {
  worker.onmessage = (event) => {
    if (event.data?.type === 'text') {
      onChunk(event.data.content)
      return
    }

    if (event.data?.type === 'done') {
      onDone()
    }
  }
  worker.postMessage({ remaining_text: text })
}
