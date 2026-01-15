import { useEffect, useState } from 'react'
import './App.css'
import TravelPage from './pages/TravelPage'
import ReplyPage from './pages/ReplyPage'
import FitnessPage from './pages/FitnessPage'
import CompletePage from './pages/CompletePage'

const App = () => {
  const [path, setPath] = useState(() => window.location.pathname)

  useEffect(() => {
    const handlePopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  if (path.startsWith('/reply')) {
    return <ReplyPage />
  }

  if (path.startsWith('/fitness')) {
    return <FitnessPage />
  }

  if (path.startsWith('/complete')) {
    return <CompletePage />
  }

  return <TravelPage />
}

export default App
