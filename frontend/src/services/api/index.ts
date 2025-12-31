import apiClient from './apiClient';
import { charactersAPI } from './charactersAPI';
import { dashboardAPI } from './dashboardAPI';
import { guestAPI } from './guestAPI';
import { authAPI } from './authAPI';
import { decisionAPI } from './decisionAPI';

/**
 * Unified API Service Layer
 * Consolidates all individual API modules into a single entry point.
 */

export const api = {
  ...charactersAPI,
  ...dashboardAPI,
  ...guestAPI,
  ...authAPI,
  ...decisionAPI,
  client: apiClient,
};

export default api;
