import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { setupChunkErrorHandler } from '@/utils/chunkRetry'

// Setup global error handler for chunk loading failures
setupChunkErrorHandler();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
