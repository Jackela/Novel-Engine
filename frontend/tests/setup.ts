import '@testing-library/jest-dom/vitest';
import { configure } from '@testing-library/dom';
import { act } from 'react';

import { afterAll, afterEach, beforeAll } from 'vitest';
import { cleanup } from './test-utils';

beforeAll(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
    true;

  configure({
    asyncWrapper: async (callback) => {
      let result: unknown;

      await act(async () => {
        result = await callback();
      });

      return result;
    },
    eventWrapper: (callback) => {
      let result: unknown;

      act(() => {
        result = callback();
      });

      return result;
    },
  });
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

afterAll(() => {
  delete (globalThis as typeof globalThis & {
    IS_REACT_ACT_ENVIRONMENT?: boolean;
  }).IS_REACT_ACT_ENVIRONMENT;
});
