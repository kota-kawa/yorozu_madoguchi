/**
 * EN: Provide the App module implementation.
 * JP: App モジュールの実装を定義する。
 */
import './App.css'
import { Route, Routes } from 'react-router-dom'
import TravelPage from './pages/TravelPage'
import ReplyPage from './pages/ReplyPage'
import FitnessPage from './pages/FitnessPage'
import JobPage from './pages/JobPage'
import StudyPage from './pages/StudyPage'
import CompletePage from './pages/CompletePage'
import UserTypeGate from './components/UserTypeGate/UserTypeGate'

/**
 * EN: Declare the App value.
 * JP: App の値を宣言する。
 */
const App = () => {
  return (
    <UserTypeGate>
      <Routes>
        <Route path="/" element={<TravelPage />} />
        <Route path="/reply" element={<ReplyPage />} />
        <Route path="/fitness" element={<FitnessPage />} />
        <Route path="/job" element={<JobPage />} />
        <Route path="/study" element={<StudyPage />} />
        <Route path="/complete" element={<CompletePage />} />
        <Route path="*" element={<TravelPage />} />
      </Routes>
    </UserTypeGate>
  )
}

export default App
