/**
 * App - Root Application Component
 * Uses TanStack Router and Query with Zustand for state
 */
import { RouterProvider } from '@tanstack/react-router';
import { AppProviders } from './app/providers';
import { router } from './app/router';
import { ErrorBoundary } from '@/shared/components/feedback/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </ErrorBoundary>
  );
}

export default App;
