/**
 * Cart TypeScript Interfaces.
 *
 * Ref: .blueprint/data.md §1D
 * Ref: .blueprint/frontend_structure.md §3B
 */

import type { UUID } from './common';
import type { ProductWithStock } from './product';

// =============================================================================
// Cart Item Types
// =============================================================================

export interface CartItem {
  product_id: UUID;
  product: ProductWithStock;
  quantity: number;
}

export interface CartItemApi {
  product_id: UUID;
  quantity: number;
}

// =============================================================================
// Cart State Types (Zustand)
// =============================================================================

export interface CartState {
  items: CartItem[];
  isLoading: boolean;
  isSyncing: boolean;
  lastSyncedAt: number | null;
}

export interface CartComputed {
  totalItems: number;
  totalQuantity: number;
  subtotal: number;
}

export interface CartActions {
  addItem: (product: ProductWithStock, quantity?: number) => void;
  removeItem: (productId: UUID) => void;
  updateQuantity: (productId: UUID, quantity: number) => void;
  clearCart: () => void;
  syncWithServer: () => Promise<void>;
}

// =============================================================================
// Cart Helpers
// =============================================================================

export function calculateCartTotals(items: CartItem[]): CartComputed {
  return items.reduce(
    (acc, item) => ({
      totalItems: acc.totalItems + 1,
      totalQuantity: acc.totalQuantity + item.quantity,
      subtotal: acc.subtotal + parseFloat(item.product.price) * item.quantity,
    }),
    { totalItems: 0, totalQuantity: 0, subtotal: 0 }
  );
}

export function isInCart(items: CartItem[], productId: UUID): boolean {
  return items.some((item) => item.product_id === productId);
}

export function getCartItem(
  items: CartItem[],
  productId: UUID
): CartItem | undefined {
  return items.find((item) => item.product_id === productId);
}

export function validateCartQuantity(
  item: CartItem
): { valid: boolean; maxQuantity: number } {
  const maxQuantity = item.product.stock;
  return {
    valid: item.quantity <= maxQuantity,
    maxQuantity,
  };
}
