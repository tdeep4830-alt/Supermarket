/**
 * Cart Store Unit Tests.
 *
 * Ref: .blueprint/frontend_structure.md §3B - Debounced server sync
 * Ref: .blueprint/data.md §1D - Shopping Cart
 *
 * Tests cover:
 *  - addItem: new item + existing item (quantity merge)
 *  - addItem: clamp quantity to available stock
 *  - removeItem
 *  - updateQuantity: normal + zero triggers remove
 *  - clearCart
 *  - getSubtotal calculation
 *  - getItemCount / getTotalQuantity
 *  - isInCart / getItem lookups
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useCartStore } from '@/store/cartStore';
import type { ProductWithStock } from '@/types/product';
import type { UUID } from '@/types/common';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeProduct(overrides: Partial<ProductWithStock> = {}): ProductWithStock {
  return {
    id: 'product-1' as UUID,
    name: 'Test Apple',
    description: 'A test product',
    price: '10.00',
    image_url: '',
    is_active: true,
    category: { id: 'cat-1' as UUID, name: 'Fruits', slug: 'fruits' },
    created_at: '2024-01-01T00:00:00Z',
    stock: 50,
    ...overrides,
  };
}

function makeProduct2(): ProductWithStock {
  return makeProduct({
    id: 'product-2' as UUID,
    name: 'Test Banana',
    price: '5.50',
    stock: 30,
  });
}

// ---------------------------------------------------------------------------
// Reset store before each test
// ---------------------------------------------------------------------------

beforeEach(() => {
  useCartStore.setState({ items: [], isLoading: false, isSyncing: false, lastSyncedAt: null });
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('cartStore', () => {
  // =========================================================================
  // addItem
  // =========================================================================

  describe('addItem', () => {
    it('adds a new item to an empty cart', () => {
      const product = makeProduct();
      useCartStore.getState().addItem(product, 3);

      const items = useCartStore.getState().items;
      expect(items).toHaveLength(1);
      expect(items[0].product_id).toBe('product-1');
      expect(items[0].quantity).toBe(3);
    });

    it('increments quantity when adding an existing product', () => {
      const product = makeProduct();
      useCartStore.getState().addItem(product, 2);
      useCartStore.getState().addItem(product, 3);

      const items = useCartStore.getState().items;
      expect(items).toHaveLength(1);
      expect(items[0].quantity).toBe(5);
    });

    it('clamps quantity to available stock', () => {
      const product = makeProduct({ stock: 5 });
      useCartStore.getState().addItem(product, 10);

      expect(useCartStore.getState().items[0].quantity).toBe(5);
    });

    it('clamps merged quantity to stock when re-adding', () => {
      const product = makeProduct({ stock: 8 });
      useCartStore.getState().addItem(product, 6);
      useCartStore.getState().addItem(product, 5);

      // 6 + 5 = 11, but stock is 8 → clamped to 8
      expect(useCartStore.getState().items[0].quantity).toBe(8);
    });

    it('defaults quantity to 1', () => {
      const product = makeProduct();
      useCartStore.getState().addItem(product);

      expect(useCartStore.getState().items[0].quantity).toBe(1);
    });
  });

  // =========================================================================
  // removeItem
  // =========================================================================

  describe('removeItem', () => {
    it('removes an item from the cart', () => {
      const p1 = makeProduct();
      const p2 = makeProduct2();
      useCartStore.getState().addItem(p1, 1);
      useCartStore.getState().addItem(p2, 2);

      useCartStore.getState().removeItem('product-1');

      const items = useCartStore.getState().items;
      expect(items).toHaveLength(1);
      expect(items[0].product_id).toBe('product-2');
    });

    it('does nothing when removing a non-existent product', () => {
      const product = makeProduct();
      useCartStore.getState().addItem(product, 1);

      useCartStore.getState().removeItem('non-existent');

      expect(useCartStore.getState().items).toHaveLength(1);
    });
  });

  // =========================================================================
  // updateQuantity
  // =========================================================================

  describe('updateQuantity', () => {
    it('updates quantity of an existing item', () => {
      const product = makeProduct();
      useCartStore.getState().addItem(product, 2);
      useCartStore.getState().updateQuantity('product-1', 7);

      expect(useCartStore.getState().items[0].quantity).toBe(7);
    });

    it('clamps to stock limit', () => {
      const product = makeProduct({ stock: 10 });
      useCartStore.getState().addItem(product, 2);
      useCartStore.getState().updateQuantity('product-1', 999);

      expect(useCartStore.getState().items[0].quantity).toBe(10);
    });

    it('removes item when quantity set to zero', () => {
      const product = makeProduct();
      useCartStore.getState().addItem(product, 5);
      useCartStore.getState().updateQuantity('product-1', 0);

      expect(useCartStore.getState().items).toHaveLength(0);
    });

    it('removes item when quantity is negative', () => {
      const product = makeProduct();
      useCartStore.getState().addItem(product, 5);
      useCartStore.getState().updateQuantity('product-1', -1);

      expect(useCartStore.getState().items).toHaveLength(0);
    });
  });

  // =========================================================================
  // clearCart
  // =========================================================================

  describe('clearCart', () => {
    it('removes all items', () => {
      useCartStore.getState().addItem(makeProduct(), 3);
      useCartStore.getState().addItem(makeProduct2(), 2);

      useCartStore.getState().clearCart();

      expect(useCartStore.getState().items).toHaveLength(0);
    });
  });

  // =========================================================================
  // Computed values
  // =========================================================================

  describe('computed values', () => {
    it('getItemCount returns number of distinct products', () => {
      useCartStore.getState().addItem(makeProduct(), 3);
      useCartStore.getState().addItem(makeProduct2(), 2);

      expect(useCartStore.getState().getItemCount()).toBe(2);
    });

    it('getTotalQuantity returns sum of all quantities', () => {
      useCartStore.getState().addItem(makeProduct(), 3);
      useCartStore.getState().addItem(makeProduct2(), 2);

      expect(useCartStore.getState().getTotalQuantity()).toBe(5);
    });

    it('getSubtotal calculates correctly', () => {
      // product-1: price 10.00, qty 3 → 30.00
      // product-2: price 5.50,  qty 2 → 11.00
      // total → 41.00
      useCartStore.getState().addItem(makeProduct(), 3);
      useCartStore.getState().addItem(makeProduct2(), 2);

      expect(useCartStore.getState().getSubtotal()).toBeCloseTo(41.0, 2);
    });

    it('getSubtotal returns 0 for empty cart', () => {
      expect(useCartStore.getState().getSubtotal()).toBe(0);
    });
  });

  // =========================================================================
  // Lookup helpers
  // =========================================================================

  describe('isInCart / getItem', () => {
    it('isInCart returns true for existing product', () => {
      useCartStore.getState().addItem(makeProduct(), 1);

      expect(useCartStore.getState().isInCart('product-1')).toBe(true);
      expect(useCartStore.getState().isInCart('product-2')).toBe(false);
    });

    it('getItem returns the CartItem or undefined', () => {
      useCartStore.getState().addItem(makeProduct(), 4);

      const item = useCartStore.getState().getItem('product-1');
      expect(item).toBeDefined();
      expect(item!.quantity).toBe(4);

      expect(useCartStore.getState().getItem('nope')).toBeUndefined();
    });
  });
});
