import { useEffect, useMemo, useState } from 'react';
import { charactersAPI } from '@/services/api/charactersAPI';

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

// Empty default state - no mock data
const DEFAULT_STATE: DashboardCharactersState = {
  characters: [],
  loading: true,
  error: null,
  source: 'fallback',
};

export const FALLBACK_DASHBOARD_CHARACTERS: DashboardCharacter[] = [
  { id: 'aria-shadowbane', name: 'Aria Shadowbane', status: 'active', role: 'protagonist', trust: 82 },
  { id: 'elder-thorne', name: 'Elder Thorne', status: 'active', role: 'npc', trust: 67 },
  { id: 'merchant-aldric', name: 'Merchant Aldric', status: 'inactive', role: 'npc', trust: 55 },
  { id: 'kael-voss', name: 'Kael Voss', status: 'active', role: 'antagonist', trust: 40 },
  { id: 'captain-lyra', name: 'Captain Lyra', status: 'active', role: 'protagonist', trust: 73 },
  { id: 'seer-mara', name: 'Seer Mara', status: 'inactive', role: 'narrator', trust: 64 },
];

function toTitle(name: string) {
  return name
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

export function useDashboardCharactersDataset() {
  const [state, setState] = useState<DashboardCharactersState>(DEFAULT_STATE);

  useEffect(() => {
    let cancelled = false;
    let fallbackTimer: NodeJS.Timeout | null = null;

    const load = async () => {
      // Ensure the dashboard can render with fallback data quickly in offline/guest contexts
      fallbackTimer = setTimeout(() => {
        if (cancelled) return;
        setState({
          characters: FALLBACK_DASHBOARD_CHARACTERS,
          loading: false,
          error: 'Using fallback dataset',
          source: 'fallback',
        });
      }, 3000);

      try {
        const response = await charactersAPI.getCharacters();
        const payload = response.data;
        const characters = (payload?.characters ?? []).map((char, index) => ({
          id: char.id || String(index),
          name: char.name || toTitle(char.id || `Character ${index + 1}`),
          status: mapCharacterStatus(char.status),
          role: mapCharacterType(char.type),
          trust: calculateTrustFromRelationships(char.relationships) ?? 50,
        }));

        if (!cancelled) {
          if (fallbackTimer) clearTimeout(fallbackTimer);
          setState({ characters, loading: false, error: null, source: 'api' });
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load dashboard data';
        if (!cancelled) {
          if (fallbackTimer) clearTimeout(fallbackTimer);
          setState({
            characters: FALLBACK_DASHBOARD_CHARACTERS,
            loading: false,
            error: message,
            source: 'fallback',
          });
        }
      }
    };

    load();

    return () => {
      cancelled = true;
      if (fallbackTimer) {
        clearTimeout(fallbackTimer);
      }
    };
  }, []);

  return useMemo(() => state, [state]);
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
