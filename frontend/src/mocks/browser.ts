import type { SetupWorker } from 'msw/browser';
import { handlers } from './handlers';

let worker: SetupWorker | null = null;

export async function startMockWorker() {
  if (typeof window === 'undefined') {
    return;
  }

  const globalScope = globalThis as typeof globalThis & {
    process?: {
      env?: Record<string, string | undefined>;
      versions?: Record<string, string | undefined>;
    };
  };
  const processRef = globalScope.process ?? { env: {} };
  if (!processRef.env) {
    processRef.env = {};
  }
  if (processRef.versions) {
    processRef.versions.node = '';
  }
  globalScope.process = processRef;

  const { setupWorker } = await import('msw/browser');
  const instance = setupWorker(...handlers);
  const activeWorker = worker ?? instance;
  worker = activeWorker;

  return activeWorker.start({
    onUnhandledRequest: 'bypass',
    serviceWorker: {
      url: '/mockServiceWorker.js',
    },
  });
}
