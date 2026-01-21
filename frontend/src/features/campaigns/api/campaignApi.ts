/**
 * Campaign API hooks using TanStack Query
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Campaign, CreateCampaignInput, UpdateCampaignInput } from '@/shared/types/campaign';

const CAMPAIGNS_KEY = ['campaigns'];

// Fetch all campaigns
export function useCampaigns() {
  return useQuery({
    queryKey: CAMPAIGNS_KEY,
    queryFn: () => api.get<Campaign[]>('/campaigns'),
  });
}

// Fetch single campaign
export function useCampaign(id: string) {
  return useQuery({
    queryKey: [...CAMPAIGNS_KEY, id],
    queryFn: () => api.get<Campaign>(`/campaigns/${id}`),
    enabled: !!id,
  });
}

// Create campaign
export function useCreateCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateCampaignInput) =>
      api.post<Campaign>('/campaigns', input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CAMPAIGNS_KEY });
    },
  });
}

// Update campaign
export function useUpdateCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...input }: UpdateCampaignInput) =>
      api.put<Campaign>(`/campaigns/${id}`, input),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: CAMPAIGNS_KEY });
      queryClient.setQueryData([...CAMPAIGNS_KEY, data.id], data);
    },
  });
}

// Delete campaign
export function useDeleteCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete(`/campaigns/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CAMPAIGNS_KEY });
    },
  });
}

// Start/Resume campaign
export function useStartCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.post<Campaign>(`/campaigns/${id}/start`),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: CAMPAIGNS_KEY });
      queryClient.setQueryData([...CAMPAIGNS_KEY, data.id], data);
    },
  });
}

// Pause campaign
export function usePauseCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.post<Campaign>(`/campaigns/${id}/pause`),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: CAMPAIGNS_KEY });
      queryClient.setQueryData([...CAMPAIGNS_KEY, data.id], data);
    },
  });
}
