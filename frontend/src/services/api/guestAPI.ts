import apiClient, { handleAPIError } from './apiClient';

export interface GuestSessionResponse {
  workspace_id: string;
  created: boolean;
}

export const guestAPI = {
  createOrResumeSession: async (): Promise<GuestSessionResponse> => {
    try {
      const response = await apiClient.post<GuestSessionResponse>('/api/guest/session');
      return response.data;
    } catch (error) {
      return handleAPIError(error);
    }
  },
};

