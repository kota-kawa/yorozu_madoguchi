export {}

declare global {
  interface SpeechRecognitionAlternativeLike {
    transcript: string
  }

  interface SpeechRecognitionResultLike {
    [index: number]: SpeechRecognitionAlternativeLike
    0: SpeechRecognitionAlternativeLike
  }

  interface SpeechRecognitionResultListLike {
    [index: number]: SpeechRecognitionResultLike
    0: SpeechRecognitionResultLike
  }

  interface SpeechRecognitionEventLike extends Event {
    results: SpeechRecognitionResultListLike
  }

  interface SpeechRecognitionErrorEventLike extends Event {
    error: string
  }

  interface SpeechRecognitionLike extends EventTarget {
    lang: string
    continuous: boolean
    interimResults: boolean
    onresult: ((event: SpeechRecognitionEventLike) => void) | null
    onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null
    onend: (() => void) | null
    start(): void
    stop(): void
  }

  interface SpeechRecognitionConstructor {
    new (): SpeechRecognitionLike
  }

  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
}
