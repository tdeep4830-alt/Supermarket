/**
 * User & Auth Types.
 *
 * Ref: .blueprint/auth.md §2A, §5
 */

import type { ISODateTime, UUID } from './common';

// =============================================================================
// User Types
// =============================================================================

export type MembershipTier = 'REGULAR' | 'GOLD' | 'PLATINUM';

export interface User {
  id: UUID;
  username: string;
  email: string;
  phone: string | null;
  is_verified: boolean;
  avatar_url: string | null;
  membership_tier: MembershipTier;
  is_staff: boolean;
  date_joined: ISODateTime;
}

// =============================================================================
// Auth Request/Response Types
// =============================================================================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  message: string;
  user: User;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  phone?: string;
}

export interface RegisterResponse {
  message: string;
  user: User;
}

export interface LogoutResponse {
  message: string;
}

export interface CSRFResponse {
  csrfToken: string;
}
