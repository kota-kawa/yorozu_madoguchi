export type WorkerInputMessage = {
  remaining_text: string
}

export type WorkerOutputMessage =
  | { type: 'text'; content: string }
  | { type: 'done' }
