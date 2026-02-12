/**
 * Toast Notification Component.
 *
 * Ref: .blueprint/frontend_structure.md §4B
 * Displays toast notifications for errors, success, etc.
 */

import { memo, useCallback } from 'react';
import { useToasts, useToastStore, type ToastType } from '@/store/toastStore';

// =============================================================================
// Toast Icon
// =============================================================================

function ToastIcon({ type }: { type: ToastType }) {
  switch (type) {
    case 'success':
      return (
        <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      );
    case 'error':
      return (
        <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      );
    case 'warning':
      return (
        <svg className="h-5 w-5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      );
    case 'info':
    default:
      return (
        <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
  }
}

// =============================================================================
// Toast Item
// =============================================================================

const typeStyles: Record<ToastType, string> = {
  success: 'border-green-200 bg-green-50',
  error: 'border-red-200 bg-red-50',
  warning: 'border-yellow-200 bg-yellow-50',
  info: 'border-blue-200 bg-blue-50',
};

interface ToastItemProps {
  id: string;
  type: ToastType;
  message: string;
}

function ToastItemComponent({ id, type, message }: ToastItemProps) {
  const removeToast = useToastStore((state) => state.removeToast);

  const handleClose = useCallback(() => {
    removeToast(id);
  }, [id, removeToast]);

  return (
    <div
      className={`flex items-start gap-3 rounded-lg border p-4 shadow-lg ${typeStyles[type]}`}
      role="alert"
    >
      <ToastIcon type={type} />
      <p className="flex-1 text-sm font-medium text-gray-800">{message}</p>
      <button
        onClick={handleClose}
        className="rounded p-1 hover:bg-black/5"
        aria-label="Close notification"
      >
        <svg className="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

const ToastItem = memo(ToastItemComponent);

// =============================================================================
// Toast Container
// =============================================================================

function ToastContainerComponent() {
  const toasts = useToasts();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} {...toast} />
      ))}
    </div>
  );
}

export const ToastContainer = memo(ToastContainerComponent);
