/**
 * Cart Store (Zustand).
 *
 * Ref: .blueprint/frontend_structure.md §1, §3B
 *
 * Features:
 * - Zustand for lightweight state management
 * - LocalStorage persistence
 * - Debounced server sync (500ms)
 * - Optimistic UI updates
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CartItem, ProductWithStock, UUID } from '@/types';

// =============================================================================
// Types
// =============================================================================

interface CartState {
  items: CartItem[];
  isLoading: boolean;
  isSyncing: boolean;
  lastSyncedAt: number | null;
}

interface CartActions {
  // Item operations
  addItem: (product: ProductWithStock, quantity?: number) => void;
  removeItem: (productId: UUID) => void;
  updateQuantity: (productId: UUID, quantity: number) => void;
  clearCart: () => void;

  // Computed values
  getItemCount: () => number;
  getTotalQuantity: () => number;
  getSubtotal: () => number;
  getItem: (productId: UUID) => CartItem | undefined;
  isInCart: (productId: UUID) => boolean;

  // Server sync
  syncWithServer: () => Promise<void>;
  setLoading: (loading: boolean) => void;
}

type CartStore = CartState & CartActions;

// =============================================================================
// Debounce utility
// =============================================================================

let syncTimeout: ReturnType<typeof setTimeout> | null = null;
const SYNC_DEBOUNCE_MS = 500; // Ref: frontend_structure.md §3B

function debouncedSync(syncFn: () => Promise<void>) {
  if (syncTimeout) {
    clearTimeout(syncTimeout);
  }
  syncTimeout = setTimeout(() => {
    syncFn();
    syncTimeout = null;
  }, SYNC_DEBOUNCE_MS);
}

// =============================================================================
// Store
// =============================================================================

export const useCartStore = create<CartStore>()(
  persist(
    (set, get) => ({
      // Initial state
      items: [],
      isLoading: false,
      isSyncing: false,
      lastSyncedAt: null,

      // =======================================================================
      // Item Operations
      // =======================================================================

      addItem: (product: ProductWithStock, quantity: number = 1) => {
        set((state) => {
          const existingIndex = state.items.findIndex(
            (item) => item.product_id === product.id
          );

          let newItems: CartItem[];

          if (existingIndex >= 0) {
            // Update existing item
            newItems = state.items.map((item, index) =>
              index === existingIndex
                ? {
                    ...item,
                    quantity: Math.min(
                      item.quantity + quantity,
                      item.product.stock // Don't exceed stock
                    ),
                    product, // Update product info (stock may have changed)
                  }
                : item
            );
          } else {
            // Add new item
            newItems = [
              ...state.items,
              {
                product_id: product.id,
                product,
                quantity: Math.min(quantity, product.stock),
              },
            ];
          }

          return { items: newItems };
        });

        // Debounced sync to server
        debouncedSync(() => get().syncWithServer());
      },

      removeItem: (productId: UUID) => {
        set((state) => ({
          items: state.items.filter((item) => item.product_id !== productId),
        }));

        debouncedSync(() => get().syncWithServer());
      },

      updateQuantity: (productId: UUID, quantity: number) => {
        if (quantity <= 0) {
          get().removeItem(productId);
          return;
        }

        set((state) => ({
          items: state.items.map((item) =>
            item.product_id === productId
              ? {
                  ...item,
                  quantity: Math.min(quantity, item.product.stock),
                }
              : item
          ),
        }));

        debouncedSync(() => get().syncWithServer());
      },

      clearCart: () => {
        set({ items: [] });
        debouncedSync(() => get().syncWithServer());
      },

      // =======================================================================
      // Computed Values
      // =======================================================================

      getItemCount: () => {
        return get().items.length;
      },

      getTotalQuantity: () => {
        return get().items.reduce((sum, item) => sum + item.quantity, 0);
      },

      getSubtotal: () => {
        return get().items.reduce(
          (sum, item) => sum + parseFloat(item.product.price) * item.quantity,
          0
        );
      },

      getItem: (productId: UUID) => {
        return get().items.find((item) => item.product_id === productId);
      },

      isInCart: (productId: UUID) => {
        return get().items.some((item) => item.product_id === productId);
      },

      // =======================================================================
      // Server Sync
      // =======================================================================

      syncWithServer: async () => {
        const { isSyncing } = get();

        // Skip if already syncing
        if (isSyncing) return;

        set({ isSyncing: true });

        try {
          // TODO: Implement actual API call when backend cart API is ready
          // const cartData = items.map(item => ({
          //   product_id: item.product_id,
          //   quantity: item.quantity,
          // }));
          // await apiClient.post('/cart/', { items: cartData });

          // Simulate sync delay
          await new Promise((resolve) => setTimeout(resolve, 100));

          set({ lastSyncedAt: Date.now() });
        } catch (error) {
          console.error('Failed to sync cart:', error);
          // Could show toast notification here
        } finally {
          set({ isSyncing: false });
        }
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },
    }),
    {
      name: 'supermarket-cart', // localStorage key
      partialize: (state) => ({
        // Only persist items, not loading states
        items: state.items,
        lastSyncedAt: state.lastSyncedAt,
      }),
    }
  )
);

// =============================================================================
// Selector Hooks (for optimized re-renders)
// =============================================================================

export const useCartItems = () => useCartStore((state) => state.items);
export const useCartItemCount = () => useCartStore((state) => state.items.length);
export const useCartTotalQuantity = () =>
  useCartStore((state) =>
    state.items.reduce((sum, item) => sum + item.quantity, 0)
  );
export const useCartSubtotal = () =>
  useCartStore((state) =>
    state.items.reduce(
      (sum, item) => sum + parseFloat(item.product.price) * item.quantity,
      0
    )
  );
export const useIsInCart = (productId: UUID) =>
  useCartStore((state) =>
    state.items.some((item) => item.product_id === productId)
  );
export const useCartItem = (productId: UUID) =>
  useCartStore((state) =>
    state.items.find((item) => item.product_id === productId)
  );
