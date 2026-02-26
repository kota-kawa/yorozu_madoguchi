/**
 * EN: Define the WorkerInputMessage type alias.
 * JP: WorkerInputMessage 型エイリアスを定義する。
 */
/**
 * EN: Provide the worker module implementation.
 * JP: worker モジュールの実装を定義する。
 */
export type WorkerInputMessage = {
  remaining_text: string
}

/**
 * EN: Define the WorkerOutputMessage type alias.
 * JP: WorkerOutputMessage 型エイリアスを定義する。
 */
export type WorkerOutputMessage =
  | { type: 'text'; content: string }
  | { type: 'done' }
