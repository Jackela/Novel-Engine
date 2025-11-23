import { useEffect, useMemo, useState } from 'react';
import { charactersAPI } from '../services/api/charactersAPI';

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
// API_BASE_URL already normalizes to an /api prefix; avoid double-prefixing
const CHARACTER_ENDPOINT = joinUrl(API_BASE_URL, '/characters');

// Empty default state - no mock data
const DEFAULT_STATE: DashboardCharactersState = {
  characters: [],
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
  // Prefer axios client to include auth headers
  try {
    const axiosResponse = await charactersAPI.getCharacters();
    const payload = axiosResponse.data;
    if (!payload || !Array.isArray(payload.characters)) {
      throw new Error('Malformed /api/characters payload');
    }

    // charactersAPI.getCharacters() now returns fully detailed Character objects
    // Transform them to DashboardCharacter format
    return payload.characters.map((char, index) => ({
      id: char.id || String(index),
      name: char.name || toTitle(char.id || `Character ${index + 1}`),
      status: mapCharacterStatus(char.status),
      role: mapCharacterType(char.type),
      trust: pseudoRandomTrust(char.id || String(index)),
    }));
  } catch {
    // Fallback to fetch if axios fails (e.g., interceptor issues)
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

    // Fetch detailed info for each character ID
    const characterDetails = await Promise.all(
      payload.characters.map(async (rawId: string, index: number) => {
        const id = String(rawId).trim().toLowerCase();
        try {
          const detailEndpoint = `${endpoint}/${id}`;
          const detailResponse = await fetch(detailEndpoint, {
            signal,
            headers: { Accept: 'application/json' },
          });
          if (!detailResponse.ok) throw new Error('Detail fetch failed');
          const detail = await detailResponse.json();
          return {
            id,
            name: detail.name || toTitle(id || `Character ${index + 1}`),
            status: mapCurrentStatusToStatus(detail.current_status),
            role: inferRoleFromCharacter(detail),
            trust: calculateTrustFromRelationships(detail.relationships) ?? pseudoRandomTrust(id),
          };
        } catch {
          return {
            id,
            name: toTitle(id || `Character ${index + 1}`),
            status: 'active' as const,
            role: 'npc' as const,
            trust: pseudoRandomTrust(id || String(index)),
          };
        }
      })
    );
    return characterDetails;
  }
}

// Map Character status to DashboardCharacter status
function mapCharacterStatus(status: string | undefined): DashboardCharacter['status'] {
  if (!status) return 'active';
  if (status === 'inactive' || status === 'archived') return 'inactive';
  return 'active';
}

// Map Character type to DashboardCharacter role
function mapCharacterType(type: string | undefined): DashboardCharacter['role'] {
  if (!type) return 'npc';
  if (type === 'protagonist') return 'protagonist';
  if (type === 'antagonist') return 'antagonist';
  if (type === 'narrator') return 'narrator';
  return 'npc';
}

// Map backend current_status to frontend status enum
function mapCurrentStatusToStatus(currentStatus: string | undefined): DashboardCharacter['status'] {
  if (!currentStatus) return 'active';
  const lower = currentStatus.toLowerCase();
  if (lower.includes('hostile') || lower.includes('enemy') || lower.includes('antagonist')) {
    return 'hostile';
  }
  if (lower.includes('inactive') || lower.includes('dormant') || lower.includes('unavailable')) {
    return 'inactive';
  }
  return 'active';
}

// Infer role from character detail data
function inferRoleFromCharacter(detail: Record<string, unknown>): DashboardCharacter['role'] {
  const narrativeContext = String(detail.narrative_context || '').toLowerCase();
  const backgroundSummary = String(detail.background_summary || '').toLowerCase();
  const combined = `${narrativeContext} ${backgroundSummary}`;

  if (combined.includes('protagonist') || combined.includes('hero') || combined.includes('main character')) {
    return 'protagonist';
  }
  if (combined.includes('antagonist') || combined.includes('villain') || combined.includes('enemy')) {
    return 'antagonist';
  }
  if (combined.includes('narrator') || combined.includes('chronicler')) {
    return 'narrator';
  }
  return 'npc';
}

// Calculate trust level from relationships data
function calculateTrustFromRelationships(relationships: Record<string, unknown> | undefined): number | null {
  if (!relationships || typeof relationships !== 'object') return null;
  const values = Object.values(relationships);
  if (values.length === 0) return null;

  // Average relationship values if they're numeric, otherwise return null
  const numericValues = values.filter((v): v is number => typeof v === 'number');
  if (numericValues.length === 0) return null;

  const avg = numericValues.reduce((a, b) => a + b, 0) / numericValues.length;
  // Normalize to 0-100 range (assuming relationships are -1 to 1 or 0 to 1)
  return Math.round(Math.min(100, Math.max(0, (avg + 1) * 50)));
}
