import { useEffect, useMemo, useState } from 'react';

export interface DashboardCharacter {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'hostile';
  role: 'protagonist' | 'antagonist' | 'npc' | 'narrator';
  trust: number;
}

interface DashboardCharactersState {
  characters: DashboardCharacter[];
  loading: boolean;
  error: string | null;
  source: 'api' | 'fallback';
}

const API_BASE_URL = resolveApiBaseUrl(
  (import.meta.env.VITE_NOVEL_ENGINE_API_BASE_URL as string | undefined) ?? 'http://127.0.0.1:8000'
);
const CHARACTER_ENDPOINT = joinUrl(API_BASE_URL, '/api/characters');

const CHARACTER_LIBRARY: Record<string, Pick<DashboardCharacter, 'name' | 'status' | 'role' | 'trust'>> = {
  aria: { name: 'Aria Shadowbane', status: 'active', role: 'protagonist', trust: 85 },
  engineer: { name: 'Kael Stormrider', status: 'active', role: 'npc', trust: 78 },
  pilot: { name: 'Captain Vex', status: 'hostile', role: 'antagonist', trust: 42 },
  scientist: { name: 'Dr. Lira Soren', status: 'inactive', role: 'npc', trust: 70 },
  test: { name: 'Systems Sentinel', status: 'inactive', role: 'narrator', trust: 60 },
};

const DEFAULT_STATE: DashboardCharactersState = {
  characters: Object.entries(CHARACTER_LIBRARY).map(([id, meta]) => ({ id, ...meta })),
  loading: true,
  error: null,
  source: 'fallback',
};

function toTitle(name: string) {
  return name
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

function pseudoRandomTrust(seed: string) {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash |= 0; // force 32-bit
  }
  const normalized = Math.abs(hash % 40);
  return 55 + normalized; // 55-94 range for consistent UI density
}

export function useDashboardCharactersDataset() {
  const [state, setState] = useState<DashboardCharactersState>(DEFAULT_STATE);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    const load = async () => {
      const endpoints = buildCharacterEndpoints();
      let lastError: string | null = 'Failed to load dashboard data';

      for (const endpoint of endpoints) {
        try {
          const mapped = await fetchCharacters(endpoint, controller.signal);
          if (cancelled) {
            return;
          }
          if (mapped.length) {
            setState({ characters: mapped, loading: false, error: null, source: 'api' });
            return;
          }
          lastError = 'Empty dataset from API';
        } catch (err) {
          if (cancelled) {
            return;
          }
          lastError = err instanceof Error ? err.message : 'Failed to load dashboard data';
        }
      }

      if (!cancelled) {
        setState((prev) => ({ ...prev, loading: false, error: lastError, source: 'fallback' }));
      }
    };

    load();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  return useMemo(() => state, [state]);
}

function joinUrl(base: string, path: string) {
  const normalizedBase = base.replace(/\/+$/, '');
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

function resolveApiBaseUrl(base: string) {
  const normalizedBase = base.replace(/\/+$/, '');
  if (/\/api\/v\d+$/i.test(normalizedBase)) {
    return normalizedBase.replace(/\/v\d+$/i, '');
  }
  if (/\/api$/i.test(normalizedBase)) {
    return normalizedBase;
  }
  return `${normalizedBase}/api`;
}

function buildCharacterEndpoints() {
  // Use /api/characters endpoints without versioning
  const endpoints: string[] = [];

  // Primary endpoint: configured API base + /api/characters
  endpoints.push(CHARACTER_ENDPOINT);

  // Same-origin proxy fallback: /api/characters
  // This allows Vite proxy to rewrite /api/* → backend /api/*
  endpoints.push('/api/characters');

  return endpoints;
}

async function fetchCharacters(endpoint: string, signal: AbortSignal): Promise<DashboardCharacter[]> {
  const response = await fetch(endpoint, {
    signal,
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`API responded with ${response.status}`);
  }

  const payload = await response.json();
  if (!payload || !Array.isArray(payload.characters)) {
    throw new Error('Malformed /api/characters payload');
  }

  return payload.characters.map((rawId: string, index: number) => {
    const id = String(rawId).trim().toLowerCase();
    const libraryEntry = CHARACTER_LIBRARY[id];
    return {
      id,
      name: libraryEntry?.name ?? toTitle(id || `Character ${index + 1}`),
      status: libraryEntry?.status ?? 'active',
      role: libraryEntry?.role ?? (index % 2 === 0 ? 'npc' : 'protagonist'),
      trust: libraryEntry?.trust ?? pseudoRandomTrust(id || String(index)),
    };
  });
}
