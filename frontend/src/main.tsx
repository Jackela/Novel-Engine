import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
import './i18n' // Initialize i18n before app starts

const rootEl = document.getElementById('root') as HTMLElement;
createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
