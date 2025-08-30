import { createSlice, PayloadAction } from '@reduxjs/toolkit';

// Placeholder campaign interfaces based on OpenAPI spec
export interface Campaign {
  id: string;
  name: string;
  description: string;
  status: 'planning' | 'active' | 'paused' | 'completed' | 'archived';
  configuration: Record<string, any>;
  participant_count: number;
  session_count: number;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface CampaignsState {
  campaigns: Campaign[];
  selectedCampaign: Campaign | null;
  loading: boolean;
  error: string | null;
}

const initialState: CampaignsState = {
  campaigns: [],
  selectedCampaign: null,
  loading: false,
  error: null,
};

const campaignsSlice = createSlice({
  name: 'campaigns',
  initialState,
  reducers: {
    setCampaigns: (state, action: PayloadAction<Campaign[]>) => {
      state.campaigns = action.payload;
    },
    setSelectedCampaign: (state, action: PayloadAction<Campaign | null>) => {
      state.selectedCampaign = action.payload;
    },
    addCampaign: (state, action: PayloadAction<Campaign>) => {
      state.campaigns.unshift(action.payload);
    },
    updateCampaign: (state, action: PayloadAction<Campaign>) => {
      const index = state.campaigns.findIndex(c => c.id === action.payload.id);
      if (index !== -1) {
        state.campaigns[index] = action.payload;
      }
    },
    removeCampaign: (state, action: PayloadAction<string>) => {
      state.campaigns = state.campaigns.filter(c => c.id !== action.payload);
      if (state.selectedCampaign?.id === action.payload) {
        state.selectedCampaign = null;
      }
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const {
  setCampaigns,
  setSelectedCampaign,
  addCampaign,
  updateCampaign,
  removeCampaign,
  setLoading,
  setError,
} = campaignsSlice.actions;

export default campaignsSlice.reducer;