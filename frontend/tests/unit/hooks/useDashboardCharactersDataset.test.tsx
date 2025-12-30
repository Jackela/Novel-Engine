import React from 'react';
import { render, waitFor, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useDashboardCharactersDataset } from '@/hooks/useDashboardCharactersDataset';
import { charactersAPI } from '@/services/api/charactersAPI';

vi.mock('@/services/api/charactersAPI', () => ({
  charactersAPI: {
    getCharacters: vi.fn(),
  },
}));

const mockedCharactersAPI = charactersAPI as unknown as {
  getCharacters: ReturnType<typeof vi.fn>;
};

describe('useDashboardCharactersDataset', () => {
  beforeEach(() => {
    mockedCharactersAPI.getCharacters.mockReset();
  });

  const renderHookComponent = () => {
    let latest: ReturnType<typeof useDashboardCharactersDataset> | null = null;
    const TestComponent = () => {
      latest = useDashboardCharactersDataset();
      return null;
    };
    render(<TestComponent />);
    return () => latest;
  };

  it('returns API characters when request succeeds', async () => {
    mockedCharactersAPI.getCharacters.mockResolvedValueOnce({
      data: {
        characters: [
          {
            id: 'alpha',
            name: 'Alpha',
            status: 'inactive',
            type: 'npc',
            relationships: { ally: 1 },
          },
        ],
      },
    });

    const getResult = renderHookComponent();

    await waitFor(() => {
      expect(getResult()?.loading).toBe(false);
      expect(getResult()?.source).toBe('api');
    });

    expect(getResult()?.characters[0]).toMatchObject({
      id: 'alpha',
      name: 'Alpha',
      status: 'inactive',
      role: 'npc',
    });
  });

  it('falls back to deterministic dataset when API fails or stalls', async () => {
    vi.useFakeTimers();
    mockedCharactersAPI.getCharacters.mockRejectedValueOnce(new Error('offline'));

    const getResult = renderHookComponent();

    await act(async () => {
      vi.runAllTimers();
    });

    await waitFor(() => {
      expect(getResult()?.loading).toBe(false);
      expect(getResult()?.source).toBe('fallback');
    });

    expect(getResult()?.characters.length).toBeGreaterThan(0);
    expect(getResult()?.characters[0].name).toBeDefined();

    vi.useRealTimers();
  });
});
