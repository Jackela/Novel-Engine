import type { z } from 'zod';
import type {
  AuthTokenSchema,
  AuthResponseSchema,
  AuthUserSchema,
  LoginRequestSchema,
} from '@/types/schemas';

export type AuthUser = z.infer<typeof AuthUserSchema>;
export type AuthToken = z.infer<typeof AuthTokenSchema>;
export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export type LoginResponse = z.infer<typeof AuthResponseSchema>;

export interface AuthState {
  isAuthenticated: boolean;
  token: AuthToken | null;
  isRefreshing: boolean;
  lastError: Error | null;
  lastLoginAt: string | null;
  isInitialized: boolean;
}
