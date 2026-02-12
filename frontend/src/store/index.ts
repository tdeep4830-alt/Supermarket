/**
 * Store Index.
 *
 * Re-exports all Zustand stores.
 */

export {
  useCartStore,
  useCartItems,
  useCartItemCount,
  useCartTotalQuantity,
  useCartSubtotal,
  useIsInCart,
  useCartItem,
} from './cartStore';

export {
  useToastStore,
  useToasts,
  useAddToast,
} from './toastStore';
export type { Toast, ToastType } from './toastStore';

export {
  useAuthStore,
  useUser,
  useIsAuthenticated,
  useAuthLoading,
  useAuthError,
  useIsAuthInitialized,
} from './authStore';
