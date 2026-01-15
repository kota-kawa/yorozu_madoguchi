import './Header.css'

const Header = () => {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="title-container">
          <h1>よろずの窓口</h1>
          <p className="subtitle">React フロントエンド ＋ Flask API</p>
        </div>
        <a href="/reply" className="nav-link-btn">
          返信作成アシスタント <span className="arrow">→</span>
        </a>
      </div>
    </header>
  )
}

export default Header
