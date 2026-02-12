/**
 * Protected Route Component.
 *
 * Ref: .blueprint/auth.md §4
 *
 * Ensures only authenticated users can access protected views.
 * Redirects to login if not authenticated.
 */

import { memo, type ReactNode } from 'react';
import { useIsAuthenticated, useIsAuthInitialized, useAuthLoading } from '@/store';

interface ProtectedRouteProps {
  children: ReactNode;
  onUnauthenticated: () => void;
  fallback?: ReactNode;
}

function ProtectedRouteComponent({
  children,
  onUnauthenticated,
  fallback,
}: ProtectedRouteProps) {
  const isAuthenticated = useIsAuthenticated();
  const isInitialized = useIsAuthInitialized();
  const isLoading = useAuthLoading();

  // Show loading state while checking auth
  if (!isInitialized || isLoading) {
    return (
      fallback || (
        <div className="flex min-h-[400px] items-center justify-center">
          <div className="text-center">
            <svg
              className="mx-auto h-8 w-8 animate-spin text-primary"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            <p className="mt-4 text-muted-foreground">Loading...</p>
          </div>
        </div>
      )
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Call the redirect handler
    onUnauthenticated();
    return null;
  }

  return <>{children}</>;
}

export const ProtectedRoute = memo(ProtectedRouteComponent);
