/**
 * Auth Store (Zustand).
 *
 * Ref: .blueprint/auth.md §7
 *
 * Features:
 * - Session-based authentication state
 * - Auto-restore session on app load via checkAuth
 * - Login, logout, register actions
 */

import { create } from 'zustand';
import type { User, LoginRequest, RegisterRequest } from '@/types';
import * as authApi from '@/api/auth';

// =============================================================================
// Types
// =============================================================================

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

type AuthStore = AuthState & AuthActions;

// =============================================================================
// Store
// =============================================================================

export const useAuthStore = create<AuthStore>((set, get) => ({
  // Initial state
  user: null,
  isAuthenticated: false,
  isLoading: false,
  isInitialized: false,
  error: null,

  // ==========================================================================
  // Actions
  // ==========================================================================

  /**
   * Login user with credentials.
   */
  login: async (credentials: LoginRequest) => {
    set({ isLoading: true, error: null });

    try {
      const response = await authApi.login(credentials);
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      const message = extractErrorMessage(error);
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: message,
      });
      throw error;
    }
  },

  /**
   * Register new user.
   * Auto-login after successful registration.
   */
  register: async (data: RegisterRequest) => {
    set({ isLoading: true, error: null });

    try {
      const response = await authApi.register(data);
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      const message = extractErrorMessage(error);
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: message,
      });
      throw error;
    }
  },

  /**
   * Logout current user.
   */
  logout: async () => {
    set({ isLoading: true, error: null });

    try {
      await authApi.logout();
    } catch (error) {
      // Ignore logout errors - clear local state anyway
      console.warn('Logout API failed:', error);
    } finally {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  },

  /**
   * Check if user is authenticated by calling /me endpoint.
   * Should be called on app initialization.
   */
  checkAuth: async () => {
    // Skip if already initialized
    if (get().isInitialized) return;

    set({ isLoading: true });

    try {
      const user = await authApi.getMe();
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
        isInitialized: true,
        error: null,
      });
    } catch {
      // User not authenticated - this is expected
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        isInitialized: true,
        error: null,
      });
    }
  },

  /**
   * Clear error state.
   */
  clearError: () => {
    set({ error: null });
  },
}));

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Extract error message from API error response.
 */
function extractErrorMessage(error: unknown): string {
  if (error && typeof error === 'object') {
    // Axios error with response
    const axiosError = error as { response?: { data?: { error?: string; details?: Record<string, string[]> } } };
    if (axiosError.response?.data?.error) {
      return axiosError.response.data.error;
    }
    // Validation errors
    if (axiosError.response?.data?.details) {
      const details = axiosError.response.data.details;
      const firstField = Object.keys(details)[0];
      if (firstField && details[firstField]?.[0]) {
        return details[firstField][0];
      }
    }
    // Generic error
    if ('message' in error && typeof error.message === 'string') {
      return error.message;
    }
  }
  return 'An unexpected error occurred';
}

// =============================================================================
// Selector Hooks (for optimized re-renders)
// =============================================================================

export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);
export const useIsAuthInitialized = () => useAuthStore((state) => state.isInitialized);
