import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import AuthGate from './AuthGate'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthGate>{session => <App key={session.user.id} user={session.user}/>}</AuthGate>
  </React.StrictMode>,
)
