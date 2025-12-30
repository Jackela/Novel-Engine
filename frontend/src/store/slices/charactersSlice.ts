import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { charactersAPI } from '@/services/api/charactersAPI';

export interface PersonalityTraits {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
}

export interface Character {
  id: string;
  name: string;
  type: 'protagonist' | 'antagonist' | 'npc' | 'narrator';
  personality_traits: PersonalityTraits;
  background: string;
  configuration: {
    ai_model: 'gpt-4' | 'gpt-3.5-turbo' | 'claude-3';
    response_style: 'formal' | 'casual' | 'dramatic' | 'humorous';
    memory_retention: 'low' | 'medium' | 'high';
  };
  status: 'active' | 'inactive' | 'archived';
  relationships?: Record<string, number>;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface CharacterListResponse {
  characters: Character[];
  pagination: {
    page: number;
    limit: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export interface CharactersState {
  characters: Character[];
  selectedCharacter: Character | null;
  pagination: CharacterListResponse['pagination'] | null;
  loading: boolean;
  error: string | null;
  filters: {
    type?: Character['type'];
    created_after?: string;
    sort: 'created_at' | 'updated_at' | 'name';
    order: 'asc' | 'desc';
  };
}

const initialState: CharactersState = {
  characters: [],
  selectedCharacter: null,
  pagination: null,
  loading: false,
  error: null,
  filters: {
    sort: 'created_at',
    order: 'desc',
  },
};

// Async thunks
export const fetchCharacters = createAsyncThunk(
  'characters/fetchCharacters',
  async (params?: {
    page?: number;
    limit?: number;
    type?: Character['type'];
    created_after?: string;
    sort?: 'created_at' | 'updated_at' | 'name';
    order?: 'asc' | 'desc';
  }) => {
    const response = await charactersAPI.getCharacters(params);
    return response;
  }
);

export const fetchCharacterById = createAsyncThunk(
  'characters/fetchCharacterById',
  async (characterId: string) => {
    const response = await charactersAPI.getCharacter(characterId);
    return response;
  }
);

export const createCharacter = createAsyncThunk(
  'characters/createCharacter',
  async (characterData: any) => {
    const response = await charactersAPI.createCharacter(characterData);
    return response;
  }
);

export const updateCharacter = createAsyncThunk(
  'characters/updateCharacter',
  async ({
    characterId,
    updates,
  }: {
    characterId: string;
    updates: any;
  }) => {
    const response = await charactersAPI.updateCharacter(characterId, updates);
    return response;
  }
);

export const deleteCharacter = createAsyncThunk(
  'characters/deleteCharacter',
  async (characterId: string) => {
    await charactersAPI.deleteCharacter(characterId);
    return characterId;
  }
);

const charactersSlice = createSlice({
  name: 'characters',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setSelectedCharacter: (state, action: PayloadAction<Character | null>) => {
      state.selectedCharacter = action.payload;
    },
    updateFilters: (
      state,
      action: PayloadAction<Partial<CharactersState['filters']>>
    ) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearCharacters: (state) => {
      state.characters = [];
      state.pagination = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch characters
      .addCase(fetchCharacters.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCharacters.fulfilled, (state, action) => {
        state.loading = false;
        if (action.payload.data) {
          state.characters = action.payload.data.characters;
          state.pagination = action.payload.data.pagination;
        }
        state.error = null;
      })
      .addCase(fetchCharacters.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch characters';
      })
      // Fetch character by ID
      .addCase(fetchCharacterById.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCharacterById.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedCharacter = action.payload.data || null;
        state.error = null;
      })
      .addCase(fetchCharacterById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch character';
      })
      // Create character
      .addCase(createCharacter.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createCharacter.fulfilled, (state, action) => {
        state.loading = false;
        if (action.payload.data) {
          state.characters.unshift(action.payload.data);
        }
        state.error = null;
      })
      .addCase(createCharacter.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to create character';
      })
      // Update character
      .addCase(updateCharacter.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateCharacter.fulfilled, (state, action) => {
        state.loading = false;
        const updatedCharacter = action.payload.data;
        if (updatedCharacter) {
          const index = state.characters.findIndex((c) => c.id === updatedCharacter.id);
          if (index !== -1) {
            state.characters[index] = updatedCharacter;
          }
          if (state.selectedCharacter?.id === updatedCharacter.id) {
            state.selectedCharacter = updatedCharacter;
          }
        }
        state.error = null;
      })
      .addCase(updateCharacter.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to update character';
      })
      // Delete character
      .addCase(deleteCharacter.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteCharacter.fulfilled, (state, action) => {
        state.loading = false;
        state.characters = state.characters.filter((c) => c.id !== action.payload);
        if (state.selectedCharacter?.id === action.payload) {
          state.selectedCharacter = null;
        }
        state.error = null;
      })
      .addCase(deleteCharacter.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to delete character';
      });
  },
});

export const {
  clearError,
  setSelectedCharacter,
  updateFilters,
  clearCharacters,
} = charactersSlice.actions;

export default charactersSlice.reducer;
