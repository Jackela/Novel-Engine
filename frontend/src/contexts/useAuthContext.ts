import { useContext } from 'react';
import { AuthContext } from './authContextStore';
import type { AuthContextState } from './authContextStore';

export const useAuthContext = (): AuthContextState => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};
