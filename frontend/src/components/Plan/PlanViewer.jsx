import './Plan.css'

const PlanViewer = ({ plan, isSubmitting, onSubmit }) => {
  return (
    <div className="card chat-card">
      <div className="card-header">
        <h1>決定している状況</h1>
      </div>
      <div className="card-body chat-messages plan-body">
        {plan ? (
          plan.split('\n').map((line, index) => (
            <p key={`${line}-${index}`} className="fade-in">
              {line}
            </p>
          ))
        ) : (
          <p className="muted">まだ決定事項はありません。</p>
        )}
      </div>
      <div className="card-footer">
        <div className="bottom-right-content">
          <button
            type="button"
            className="btn-decide"
            id="sendBu"
            onClick={onSubmit}
            disabled={!plan || isSubmitting}
          >
            <i className="bi bi-check-circle-fill" aria-hidden /> 決定
          </button>
        </div>
      </div>
    </div>
  )
}

export default PlanViewer
