/**
 * Cart Button Component.
 *
 * Floating cart button for header with item count badge.
 */

import { memo } from 'react';
import { useCartTotalQuantity, useCartSubtotal } from '@/store';
import { formatPrice } from '@/utils';

interface CartButtonProps {
  onClick: () => void;
}

function CartButtonComponent({ onClick }: CartButtonProps) {
  const totalQuantity = useCartTotalQuantity();
  const subtotal = useCartSubtotal();

  return (
    <button
      onClick={onClick}
      className="relative flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
    >
      {/* Cart Icon */}
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
          d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
        />
      </svg>

      {/* Text */}
      <span>購物車</span>

      {/* Count Badge */}
      {totalQuantity > 0 && (
        <>
          <span className="rounded-full bg-white/20 px-2 py-0.5 text-xs">
            {totalQuantity}
          </span>
          <span className="hidden text-xs opacity-80 sm:inline">
            {formatPrice(subtotal)}
          </span>
        </>
      )}

      {/* Animated Badge */}
      {totalQuantity > 0 && (
        <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-xs font-bold text-white">
          {totalQuantity > 99 ? '99+' : totalQuantity}
        </span>
      )}
    </button>
  );
}

export const CartButton = memo(CartButtonComponent);
