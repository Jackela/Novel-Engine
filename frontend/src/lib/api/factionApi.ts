/**
 * Faction API Client (CHAR-036)
 *
 * Provides API functions for fetching faction data including
 * faction details and member lists.
 */
import { api } from './client';
import {
  FactionDetailResponseSchema,
  type FactionDetailResponse,
} from '@/types/schemas';

/**
 * Fetch faction details including member list.
 *
 * @param factionId - The UUID of the faction to retrieve
 * @returns Faction details with member list
 */
export async function getFactionDetail(factionId: string): Promise<FactionDetailResponse> {
  const data = await api.get<unknown>(`/factions/${factionId}`);
  return FactionDetailResponseSchema.parse(data);
}
