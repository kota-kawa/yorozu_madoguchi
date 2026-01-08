import './Chat.css'

const ChatInput = ({
  input,
  onInputChange,
  onKeyDown,
  onSubmit,
  onToggleInfo,
  disabled,
}) => {
  return (
    <div className="chat-input">
      <button
        type="button"
        id="information"
        className="btn-info original-btn"
        onClick={onToggleInfo}
        aria-label="入力例を表示"
      >
        <i className="bi bi-info-circle-fill" aria-hidden />
      </button>

      <form className="chat-form" onSubmit={onSubmit}>
        <textarea
          id="message"
          name="message"
          placeholder="メッセージを入力．．．"
          rows="1"
          maxLength={3000}
          value={input}
          onChange={onInputChange}
          onKeyDown={onKeyDown}
        />
        <button
          type="submit"
          className="btn-chat original-btn"
          disabled={disabled}
          aria-label="送信"
        >
          <i className="bi bi-send-fill" aria-hidden />
        </button>
      </form>
    </div>
  )
}

export default ChatInput
