import { combineReducers } from '@reduxjs/toolkit';
import authSlice from './slices/authSlice';
import charactersSlice from './slices/charactersSlice';
import storiesSlice from './slices/storiesSlice';
import campaignsSlice from './slices/campaignsSlice';
import dashboardSlice from './slices/dashboardSlice';
import decisionSlice from './slices/decisionSlice';

export const rootReducer = combineReducers({
  auth: authSlice,
  characters: charactersSlice,
  stories: storiesSlice,
  campaigns: campaignsSlice,
  dashboard: dashboardSlice,
  decision: decisionSlice,
});

export type RootState = ReturnType<typeof rootReducer>;
