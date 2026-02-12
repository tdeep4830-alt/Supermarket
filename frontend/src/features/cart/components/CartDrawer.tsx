/**
 * Cart Drawer Component.
 *
 * Ref: .blueprint/frontend_structure.md §2
 * Slide-out cart panel showing items and totals.
 */

import { memo, useCallback } from 'react';
import {
  useCartStore,
  useCartItems,
  useCartSubtotal,
  useCartTotalQuantity,
} from '@/store';
import { formatPrice } from '@/utils';
import { CartItem } from './CartItem';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onCheckout?: () => void;
}

function CartDrawerComponent({ isOpen, onClose, onCheckout }: CartDrawerProps) {
  const items = useCartItems();
  const subtotal = useCartSubtotal();
  const totalQuantity = useCartTotalQuantity();
  const clearCart = useCartStore((state) => state.clearCart);
  const isSyncing = useCartStore((state) => state.isSyncing);

  const handleClearCart = useCallback(() => {
    if (confirm('確定要清空購物車嗎？')) {
      clearCart();
    }
  }, [clearCart]);

  const handleCheckout = useCallback(() => {
    onCheckout?.();
    onClose();
  }, [onCheckout, onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={`fixed right-0 top-0 z-50 h-full w-full max-w-md transform bg-background shadow-xl transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">購物車</h2>
            <span className="rounded-full bg-primary px-2 py-0.5 text-xs text-primary-foreground">
              {totalQuantity}
            </span>
            {isSyncing && (
              <span className="text-xs text-muted-foreground">同步中...</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-2 hover:bg-accent"
            aria-label="關閉購物車"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex h-[calc(100%-180px)] flex-col overflow-y-auto p-4">
          {items.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <svg
                className="mb-4 h-16 w-16 text-muted-foreground/50"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
              <p className="text-muted-foreground">購物車是空的</p>
              <button
                onClick={onClose}
                className="mt-4 text-sm text-primary hover:underline"
              >
                繼續購物
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {items.map((item) => (
                <CartItem key={item.product_id} item={item} />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="absolute bottom-0 left-0 right-0 border-t border-border bg-background p-4">
            {/* Subtotal */}
            <div className="mb-4 flex items-center justify-between">
              <span className="text-muted-foreground">小計</span>
              <span className="text-xl font-bold">{formatPrice(subtotal)}</span>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <button
                onClick={handleCheckout}
                className="w-full rounded-md bg-primary py-3 font-medium text-primary-foreground hover:bg-primary/90"
              >
                前往結帳
              </button>
              <button
                onClick={handleClearCart}
                className="w-full rounded-md border border-border py-2 text-sm text-muted-foreground hover:bg-accent"
              >
                清空購物車
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export const CartDrawer = memo(CartDrawerComponent);
