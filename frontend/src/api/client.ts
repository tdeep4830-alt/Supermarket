/**
 * Axios API Client Configuration.
 *
 * Ref: .blueprint/frontend_structure.md §1
 * Central API client with interceptors for error handling and logging.
 */

import axios, { type AxiosError, type AxiosInstance } from 'axios';
import type { ApiError } from '@/types';
import { isApiError } from '@/types';

// =============================================================================
// Error Reporting Interface (Sentry Integration Point)
// =============================================================================

/**
 * Error context for external error reporting services.
 */
export interface ErrorReportContext {
  url: string;
  method: string;
  status: number;
  statusText: string;
  errorCode: string | null;
  errorMessage: string | null;
  requestData?: unknown;
  responseData?: unknown;
  timestamp: string;
}

/**
 * Error reporter interface for external services (e.g., Sentry).
 *
 * Usage:
 * ```ts
 * import * as Sentry from '@sentry/react';
 *
 * setErrorReporter({
 *   captureException: (error, context) => {
 *     Sentry.captureException(error, {
 *       tags: { status: context.status, errorCode: context.errorCode },
 *       extra: context,
 *     });
 *   },
 *   captureMessage: (message, context) => {
 *     Sentry.captureMessage(message, {
 *       level: 'error',
 *       extra: context,
 *     });
 *   },
 * });
 * ```
 */
export interface ErrorReporter {
  captureException: (error: Error, context: ErrorReportContext) => void;
  captureMessage: (message: string, context: ErrorReportContext) => void;
}

let errorReporter: ErrorReporter | null = null;

/**
 * Set the error reporter for external service integration.
 */
export function setErrorReporter(reporter: ErrorReporter): void {
  errorReporter = reporter;
}

/**
 * Get the current error reporter instance.
 */
export function getErrorReporter(): ErrorReporter | null {
  return errorReporter;
}

// =============================================================================
// Error Logging Utilities
// =============================================================================

/**
 * Build error context from Axios error.
 */
function buildErrorContext(error: AxiosError<ApiError>): ErrorReportContext {
  const { config, response } = error;

  let errorCode: string | null = null;
  let errorMessage: string | null = null;

  if (response?.data && isApiError(response.data)) {
    errorCode = response.data.error.code;
    errorMessage = response.data.error.message;
  }

  return {
    url: config?.url || 'unknown',
    method: (config?.method || 'unknown').toUpperCase(),
    status: response?.status || 0,
    statusText: response?.statusText || 'Unknown Error',
    errorCode,
    errorMessage,
    requestData: config?.data ? safeJsonParse(config.data) : undefined,
    responseData: response?.data,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Safely parse JSON string, return original if parse fails.
 */
function safeJsonParse(data: unknown): unknown {
  if (typeof data === 'string') {
    try {
      return JSON.parse(data);
    } catch {
      return data;
    }
  }
  return data;
}

/**
 * Log error to console with structured format.
 */
function logErrorToConsole(
  _error: AxiosError<ApiError>,
  context: ErrorReportContext,
  severity: 'error' | 'warn' = 'error'
): void {
  const logMethod = severity === 'error' ? console.error : console.warn;

  logMethod(
    `[API ${severity.toUpperCase()}] ${context.method} ${context.url}`,
    {
      status: context.status,
      statusText: context.statusText,
      errorCode: context.errorCode,
      errorMessage: context.errorMessage,
      timestamp: context.timestamp,
      response: context.responseData,
      request: context.requestData,
    }
  );
}

/**
 * Report error to external service if configured.
 */
function reportToExternalService(
  _error: AxiosError<ApiError>,
  context: ErrorReportContext
): void {
  if (!errorReporter) return;

  const status = context.status;

  // Report server errors (5xx) as exceptions
  if (status >= 500) {
    errorReporter.captureException(
      new Error(`API Error: ${context.method} ${context.url} returned ${status}`),
      context
    );
  } else {
    // Report client errors (4xx) as messages
    errorReporter.captureMessage(
      `API ${context.method} ${context.url}: ${context.errorCode || status}`,
      context
    );
  }
}

// =============================================================================
// API Client Instance
// =============================================================================

const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // For session authentication
});

// =============================================================================
// Request Interceptor
// =============================================================================

apiClient.interceptors.request.use(
  (config) => {
    // Add CSRF token if available (Django)
    const csrfToken = document.cookie
      .split('; ')
      .find((row) => row.startsWith('csrftoken='))
      ?.split('=')[1];

    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// =============================================================================
// Response Interceptor
// =============================================================================

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const status = error.response?.status || 0;
    const context = buildErrorContext(error);

    // Log all failed requests
    if (status >= 400) {
      // 409 Conflict & 5xx Server Errors - detailed console output
      if (status === 409 || status >= 500) {
        logErrorToConsole(error, context, 'error');

        // Additional detailed output for debugging
        console.group(`[API ERROR DETAILS] ${context.method} ${context.url}`);
        console.error('Status:', status, context.statusText);
        console.error('Error Code:', context.errorCode);
        console.error('Error Message:', context.errorMessage);
        console.error('Timestamp:', context.timestamp);
        if (context.responseData) {
          console.error('Response Data:', context.responseData);
        }
        if (context.requestData) {
          console.error('Request Data:', context.requestData);
        }
        console.groupEnd();

        // Report to external service (Sentry)
        reportToExternalService(error, context);
      } else {
        // Other 4xx errors - warning level
        logErrorToConsole(error, context, 'warn');
      }
    }

    // Handle 401 Unauthorized - redirect to login
    if (status === 401) {
      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

export default apiClient;
