/**
 * EN: Provide the speech.d module implementation.
 * JP: speech.d モジュールの実装を定義する。
 */
export {}

declare global {
  /**
   * EN: Define the SpeechRecognitionAlternativeLike interface contract.
   * JP: SpeechRecognitionAlternativeLike インターフェース契約を定義する。
   */
  interface SpeechRecognitionAlternativeLike {
    transcript: string
  }

  /**
   * EN: Define the SpeechRecognitionResultLike interface contract.
   * JP: SpeechRecognitionResultLike インターフェース契約を定義する。
   */
  interface SpeechRecognitionResultLike {
    [index: number]: SpeechRecognitionAlternativeLike
    0: SpeechRecognitionAlternativeLike
  }

  /**
   * EN: Define the SpeechRecognitionResultListLike interface contract.
   * JP: SpeechRecognitionResultListLike インターフェース契約を定義する。
   */
  interface SpeechRecognitionResultListLike {
    [index: number]: SpeechRecognitionResultLike
    0: SpeechRecognitionResultLike
  }

  /**
   * EN: Define the SpeechRecognitionEventLike interface contract.
   * JP: SpeechRecognitionEventLike インターフェース契約を定義する。
   */
  interface SpeechRecognitionEventLike extends Event {
    results: SpeechRecognitionResultListLike
  }

  /**
   * EN: Define the SpeechRecognitionErrorEventLike interface contract.
   * JP: SpeechRecognitionErrorEventLike インターフェース契約を定義する。
   */
  interface SpeechRecognitionErrorEventLike extends Event {
    error: string
  }

  /**
   * EN: Define the SpeechRecognitionLike interface contract.
   * JP: SpeechRecognitionLike インターフェース契約を定義する。
   */
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

  /**
   * EN: Define the SpeechRecognitionConstructor interface contract.
   * JP: SpeechRecognitionConstructor インターフェース契約を定義する。
   */
  interface SpeechRecognitionConstructor {
    new (): SpeechRecognitionLike
  }

  /**
   * EN: Define the Window interface contract.
   * JP: Window インターフェース契約を定義する。
   */
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
}
