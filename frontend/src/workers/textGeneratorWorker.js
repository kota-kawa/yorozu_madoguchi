self.onmessage = (event) => {
  const remainingText = event.data?.remaining_text || ''
  let index = 0

  // 以前の40msから15msに短縮し、よりスムーズに表示されるようにする
  const interval = setInterval(() => {
    if (index < remainingText.length) {
      // 処理落ちを防ぐため、長いテキストの場合は一度に送る文字数を少し増やすなどの調整も考えられるが
      // まずは単純に頻度を上げる
      self.postMessage({ type: 'text', content: remainingText.charAt(index) })
      index += 1
      return
    }

    clearInterval(interval)
    self.postMessage({ type: 'done' })
  }, 15)
}