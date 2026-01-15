import { useEffect, useState } from 'react'
import './App.css'
import TravelPage from './pages/TravelPage'
import ReplyPage from './pages/ReplyPage'
import FitnessPage from './pages/FitnessPage'
import CompletePage from './pages/CompletePage'
import UserTypeGate from './components/UserTypeGate/UserTypeGate'

const App = () => {
  const [path, setPath] = useState(() => window.location.pathname)

  useEffect(() => {
    const handlePopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  let content = <TravelPage />

  if (path.startsWith('/reply')) {
    content = <ReplyPage />
  } else if (path.startsWith('/fitness')) {
    content = <FitnessPage />
  } else if (path.startsWith('/complete')) {
    content = <CompletePage />
  }

  return <UserTypeGate>{content}</UserTypeGate>
}

export default App
