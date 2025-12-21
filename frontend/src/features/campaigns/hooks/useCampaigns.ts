import { useState, useEffect } from 'react';
import type { Campaign } from '@/types/campaign';

// Mock data (moved from Component)
const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: '1',
    name: 'Operation: Silent Echo',
    description: 'A covert infiltration mission on Meridian Station.',
    status: 'active',
    created_at: '2025-12-01T10:00:00Z',
    updated_at: '2025-12-03T09:30:00Z',
    current_turn: 12,
  },
  {
    id: '2',
    name: 'The Red Protocol',
    description: 'Diplomatic negotiations with the Martian delegation.',
    status: 'completed',
    created_at: '2025-11-20T14:00:00Z',
    updated_at: '2025-11-25T16:45:00Z',
    current_turn: 45,
  },
  {
    id: '3',
    name: 'Void Drifters',
    description: 'Survival scenario in the outer asteroid belt.',
    status: 'archived',
    created_at: '2025-10-15T08:00:00Z',
    updated_at: '2025-10-20T11:20:00Z',
    current_turn: 8,
  }
];

export const useCampaigns = () => {
  const [data, setData] = useState<Campaign[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error] = useState<Error | null>(null);

  useEffect(() => {
    // Simulate API call
    const timer = setTimeout(() => {
      setData(MOCK_CAMPAIGNS);
      setIsLoading(false);
    }, 800);

    return () => clearTimeout(timer);
  }, []);

  return { data, isLoading, error };
};
