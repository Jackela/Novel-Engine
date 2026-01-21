/**
 * Application Entry Point
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App';
import './styles/tailwind.css';

const rootEl = document.getElementById('root');

if (!rootEl) {
  throw new Error('Root element not found');
}

const renderApp = () => {
  createRoot(rootEl).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
};

const prepareApp = async () => {
  if (import.meta.env.DEV && import.meta.env.VITE_ENABLE_MSW === 'true') {
    try {
      const { startMockWorker } = await import('./mocks/browser');
      await startMockWorker();
    } catch (error) {
      console.warn('MSW worker failed to start. Continuing without mocks.', error);
    }
  }

  renderApp();
};

void prepareApp();
