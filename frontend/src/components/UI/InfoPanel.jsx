import './UI.css'

const InfoPanel = ({ isOpen, samples, onSelect }) => {
  return (
    <div className={`info-text ${isOpen ? 'open' : ''}`}>
      <h2>入力の例</h2>
      <div className="option-list">
        {samples.map((sample) => (
          <button
            key={sample}
            type="button"
            className="sample-option"
            onClick={() => onSelect(sample)}
          >
            {sample}
          </button>
        ))}
      </div>
    </div>
  )
}

export default InfoPanel
