import { createSlice, PayloadAction } from '@reduxjs/toolkit';

// Placeholder story interfaces based on OpenAPI spec
export interface Story {
  id: string;
  title: string;
  genre: 'fantasy' | 'sci-fi' | 'mystery' | 'romance' | 'horror' | 'adventure' | 'drama' | 'comedy';
  themes: string[];
  content: string;
  quality_score: number;
  word_count: number;
  characters: string[];
  status: 'generating' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface StoriesState {
  stories: Story[];
  selectedStory: Story | null;
  loading: boolean;
  error: string | null;
}

const initialState: StoriesState = {
  stories: [],
  selectedStory: null,
  loading: false,
  error: null,
};

const storiesSlice = createSlice({
  name: 'stories',
  initialState,
  reducers: {
    setStories: (state, action: PayloadAction<Story[]>) => {
      state.stories = action.payload;
    },
    setSelectedStory: (state, action: PayloadAction<Story | null>) => {
      state.selectedStory = action.payload;
    },
    addStory: (state, action: PayloadAction<Story>) => {
      state.stories.unshift(action.payload);
    },
    updateStory: (state, action: PayloadAction<Story>) => {
      const index = state.stories.findIndex(s => s.id === action.payload.id);
      if (index !== -1) {
        state.stories[index] = action.payload;
      }
    },
    removeStory: (state, action: PayloadAction<string>) => {
      state.stories = state.stories.filter(s => s.id !== action.payload);
      if (state.selectedStory?.id === action.payload) {
        state.selectedStory = null;
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
  setStories,
  setSelectedStory,
  addStory,
  updateStory,
  removeStory,
  setLoading,
  setError,
} = storiesSlice.actions;

export default storiesSlice.reducer;