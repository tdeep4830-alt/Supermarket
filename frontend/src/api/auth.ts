/**
 * Auth API Functions.
 *
 * Ref: .blueprint/auth.md §5, §7
 */

import apiClient from './client';
import type {
  CSRFResponse,
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  RegisterRequest,
  RegisterResponse,
  User,
} from '@/types';

// =============================================================================
// CSRF Token
// =============================================================================

/**
 * Fetch CSRF token from server.
 * Should be called before any POST/PUT/DELETE request if no token exists.
 */
export async function fetchCSRFToken(): Promise<string> {
  const response = await apiClient.get<CSRFResponse>('/auth/csrf/');
  return response.data.csrfToken;
}

// =============================================================================
// Auth API
// =============================================================================

/**
 * Register a new user.
 *
 * POST /api/auth/register/
 */
export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  const response = await apiClient.post<RegisterResponse>('/auth/register/', data);
  return response.data;
}

/**
 * Login user.
 *
 * POST /api/auth/login/
 */
export async function login(data: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login/', data);
  return response.data;
}

/**
 * Logout current user.
 *
 * POST /api/auth/logout/
 */
export async function logout(): Promise<LogoutResponse> {
  const response = await apiClient.post<LogoutResponse>('/auth/logout/');
  return response.data;
}

/**
 * Get current authenticated user.
 *
 * GET /api/auth/me/
 */
export async function getMe(): Promise<User> {
  const response = await apiClient.get<User>('/auth/me/');
  return response.data;
}

/**
 * Update current user profile.
 *
 * PUT /api/auth/me/
 */
export async function updateMe(
  data: Partial<Pick<User, 'email' | 'phone' | 'avatar_url'>>
): Promise<User> {
  const response = await apiClient.put<User>('/auth/me/', data);
  return response.data;
}
