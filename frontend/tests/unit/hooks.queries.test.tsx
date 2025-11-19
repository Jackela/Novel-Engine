import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import * as queries from '@/services/queries';
import api from '@/services/api';

function HookProbe() {
  const { data, isLoading, error } = queries.useCharactersQuery();
  if (isLoading) return <div>loading</div>;
  if (error) return <div>error</div>;
  return <div>count:{(data ?? []).length}</div>;
}

describe('US3: Query hooks states', () => {
  it('loading -> data success flow', async () => {
    vi.spyOn(api, 'getCharacters').mockResolvedValueOnce(['a', 'b']);
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await act(async () => {
      render(
        <QueryClientProvider client={qc}>
          <HookProbe />
        </QueryClientProvider>
      );
    });
    await waitFor(async () => {
      expect(await screen.findByText('count:2')).toBeTruthy();
    });
  });

  it('error flow', async () => {
    vi.spyOn(api, 'getCharacters').mockRejectedValueOnce(new Error('boom'));
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    await act(async () => {
      render(
        <QueryClientProvider client={qc}>
          <HookProbe />
        </QueryClientProvider>
      );
    });
    await waitFor(async () => {
      expect(await screen.findByText('error')).toBeTruthy();
    });
  });
});
