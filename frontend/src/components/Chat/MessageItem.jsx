import './Chat.css'

const MessageItem = ({ message, onYesNo, disabled }) => {
  return (
    <div className={`chat-message ${message.sender}`}>
      <p>{message.text}</p>
      {message.type === 'yesno' && (
        <div className="button-container">
          <button
            type="button"
            className="btn btn-yes"
            onClick={() => onYesNo('はい')}
            disabled={disabled}
          >
            はい　<i className="bi bi-hand-thumbs-up-fill" aria-hidden />
          </button>
          <button
            type="button"
            className="btn btn-no"
            onClick={() => onYesNo('いいえ')}
            disabled={disabled}
          >
            いいえ <i className="bi bi-hand-thumbs-down-fill" aria-hidden />
          </button>
        </div>
      )}
      {message.type === 'selection' && (
        <div className="button-container selection-container">
          {message.choices.map((choice, index) => (
            <button
              key={index}
              type="button"
              className="btn btn-option"
              onClick={() => onYesNo(choice)}
              disabled={disabled}
            >
              {choice}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default MessageItem
