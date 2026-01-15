import './Header.css'

const Header = ({
  title = 'よろずの窓口',
  subtitle = 'React フロントエンド ＋ Flask API',
  linkHref = '/reply',
  linkLabel = '返信作成アシスタント',
}) => {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="title-container">
          <h1>{title}</h1>
          <p className="subtitle">{subtitle}</p>
        </div>
        <a href={linkHref} className="nav-link-btn">
          {linkLabel} <span className="arrow">→</span>
        </a>
      </div>
    </header>
  )
}

export default Header
