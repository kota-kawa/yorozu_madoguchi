self.onmessage = (event) => {
  const remainingText = event.data?.remaining_text || ''
  let index = 0

  const interval = setInterval(() => {
    if (index < remainingText.length) {
      self.postMessage({ type: 'text', content: remainingText.charAt(index) })
      index += 1
      return
    }

    clearInterval(interval)
    self.postMessage({ type: 'done' })
  }, 40)
}
