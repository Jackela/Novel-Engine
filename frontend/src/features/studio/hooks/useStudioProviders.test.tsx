import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '@/app/api';
import type { ProviderInfo } from '@/app/types/studio';

import { useStudioProviders } from './useStudioProviders';

vi.mock('@/app/api', () => ({
  api: {
    providers: vi.fn(),
  },
}));

const mountedContainers: Array<{ container: HTMLDivElement; root: ReturnType<typeof createRoot> }> =
  [];

afterEach(() => {
  for (const { container, root } of mountedContainers) {
    act(() => {
      root.unmount();
    });
    container.remove();
  }
  mountedContainers.length = 0;
});

function renderHook<T>(useHook: () => T): { result: { current: T } } {
  const result = { current: undefined as unknown as T };

  function Wrapper() {
    result.current = useHook();
    return null;
  }

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  mountedContainers.push({ container, root });

  act(() => {
    root.render(<Wrapper />);
  });

  return { result };
}

describe('useStudioProviders', () => {
  it('returns fallback providers before the API responds', () => {
    vi.mocked(api.providers).mockResolvedValue({ providers: [] });

    const { result } = renderHook(() => useStudioProviders());

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual([
      'mock',
      'dashscope',
      'openai_compatible',
    ]);
  });

  it('replaces fallback providers with API results once loaded', async () => {
    vi.mocked(api.providers).mockResolvedValue({
      providers: [
        { provider: 'openai_compatible', configured: true, model: 'gpt-4o', is_default: true },
        { provider: 'mock', configured: true, model: null, is_default: false },
      ],
    });

    const { result } = renderHook(() => useStudioProviders());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual([
      'openai_compatible',
      'mock',
    ]);
  });

  it('keeps fallback providers when the API fails', async () => {
    vi.mocked(api.providers).mockRejectedValue(new Error('offline'));

    const { result } = renderHook(() => useStudioProviders());

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.map((item: ProviderInfo) => item.provider)).toEqual([
      'mock',
      'dashscope',
      'openai_compatible',
    ]);
  });
});
