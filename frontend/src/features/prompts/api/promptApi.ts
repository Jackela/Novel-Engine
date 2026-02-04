/**
 * Prompt API hooks using TanStack Query
 *
 * BRAIN-019A: Prompt Lab - List View
 * Provides hooks for interacting with the prompt management API.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  PromptListResponseSchema,
  PromptDetailResponseSchema,
  PromptTagsResponseSchema,
} from '@/types/schemas';
import type {
  PromptDetailResponse,
  PromptCreateRequest,
  PromptUpdateRequest,
  PromptRenderRequest,
  PromptRenderResponse,
  PromptGenerateRequest,
  PromptGenerateResponse,
} from '@/types/schemas';

const PROMPTS_KEY = ['prompts'];

// Fetch all prompts with optional filters
export function usePrompts(filters?: {
  tags?: string;
  model?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: [...PROMPTS_KEY, 'list', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.tags) params.set('tags', filters.tags);
      if (filters?.model) params.set('model', filters.model);
      if (filters?.limit !== undefined) params.set('limit', String(filters.limit));
      if (filters?.offset !== undefined) params.set('offset', String(filters.offset));

      const queryString = params.toString();
      const url = `/prompts${queryString ? `?${queryString}` : ''}`;
      const data = await api.get<unknown>(url);
      const parsed = PromptListResponseSchema.parse(data);
      return parsed;
    },
  });
}

// Search prompts by query string
export function usePromptsSearch(query: string, limit: number = 20) {
  return useQuery({
    queryKey: [...PROMPTS_KEY, 'search', query, limit],
    queryFn: async () => {
      if (!query.trim()) {
        return { prompts: [], total: 0, limit, offset: 0 };
      }
      const data = await api.get<unknown>(`/prompts/search?query=${encodeURIComponent(query)}&limit=${limit}`);
      const parsed = PromptListResponseSchema.parse(data);
      return parsed;
    },
    enabled: query.trim().length > 0,
  });
}

// Fetch single prompt by ID
export function usePrompt(id: string) {
  return useQuery({
    queryKey: [...PROMPTS_KEY, 'detail', id],
    queryFn: async () => {
      const data = await api.get<unknown>(`/prompts/${id}`);
      return PromptDetailResponseSchema.parse(data);
    },
    enabled: !!id,
  });
}

// Fetch prompt versions
export function usePromptVersions(id: string) {
  return useQuery({
    queryKey: [...PROMPTS_KEY, 'versions', id],
    queryFn: async () => {
      const data = await api.get<unknown>(`/prompts/${id}/versions`);
      const parsed = PromptListResponseSchema.parse(data);
      return parsed;
    },
    enabled: !!id,
  });
}

// Fetch all available tags
export function usePromptTags() {
  return useQuery({
    queryKey: [...PROMPTS_KEY, 'tags'],
    queryFn: async () => {
      const data = await api.get<unknown>('/prompts/tags');
      return PromptTagsResponseSchema.parse(data);
    },
  });
}

// Create prompt
export function useCreatePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: PromptCreateRequest) =>
      api.post<PromptDetailResponse>('/prompts', input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROMPTS_KEY });
    },
  });
}

// Update prompt (creates new version)
export function useUpdatePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...input }: PromptUpdateRequest & { id: string }) =>
      api.put<PromptDetailResponse>(`/prompts/${id}`, input),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: PROMPTS_KEY });
      queryClient.invalidateQueries({ queryKey: [...PROMPTS_KEY, 'detail', variables.id] });
      queryClient.invalidateQueries({ queryKey: [...PROMPTS_KEY, 'versions', variables.id] });
    },
  });
}

// Delete prompt
export function useDeletePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete(`/prompts/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROMPTS_KEY });
    },
  });
}

// Render prompt with variables
export function useRenderPrompt() {
  return useMutation({
    mutationFn: ({ id, variables, strict = true }: {
      id: string;
      variables?: Array<{ name: string; value: unknown }>;
      strict?: boolean;
    }) => {
      const payload: PromptRenderRequest = {
        variables: variables || [],
        strict,
      };
      return api.post<PromptRenderResponse>(`/prompts/${id}/render`, payload);
    },
  });
}

// Generate output using prompt with variables
// BRAIN-020B: Frontend: Prompt Playground - Integration
export function useGeneratePrompt() {
  return useMutation({
    mutationFn: ({ id, config, variables }: {
      id: string;
      variables?: Array<{ name: string; value: unknown }>;
      config?: {
        provider?: string;
        model_name?: string;
        temperature?: number;
        max_tokens?: number;
        top_p?: number;
        frequency_penalty?: number;
        presence_penalty?: number;
      };
      strict?: boolean;
    }) => {
      const payload: PromptGenerateRequest = {
        variables: variables || [],
        provider: config?.provider,
        model_name: config?.model_name,
        temperature: config?.temperature,
        max_tokens: config?.max_tokens,
        top_p: config?.top_p,
        frequency_penalty: config?.frequency_penalty,
        presence_penalty: config?.presence_penalty,
        strict: true,
      };
      return api.post<PromptGenerateResponse>(`/prompts/${id}/generate`, payload);
    },
  });
}

// Rollback prompt to specific version
export function useRollbackPrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, version }: { id: string; version: number }) =>
      api.post<PromptDetailResponse>(`/prompts/${id}/rollback/${version}`, {}),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: PROMPTS_KEY });
      queryClient.invalidateQueries({ queryKey: [...PROMPTS_KEY, 'detail', variables.id] });
      queryClient.invalidateQueries({ queryKey: [...PROMPTS_KEY, 'versions', variables.id] });
    },
  });
}
