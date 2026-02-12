/**
 * Cart Item Component.
 *
 * Ref: .blueprint/frontend_structure.md §3B
 * Individual cart item with quantity controls.
 */

import { memo, useCallback } from 'react';
import { useCartStore } from '@/store';
import type { CartItem as CartItemType } from '@/types';
import { formatPrice } from '@/utils';

interface CartItemProps {
  item: CartItemType;
}

function CartItemComponent({ item }: CartItemProps) {
  const { product, quantity } = item;
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const removeItem = useCartStore((state) => state.removeItem);

  const isMaxQuantity = quantity >= product.stock;
  const itemTotal = parseFloat(product.price) * quantity;

  const handleIncrement = useCallback(() => {
    if (quantity < product.stock) {
      updateQuantity(product.id, quantity + 1);
    }
  }, [product.id, product.stock, quantity, updateQuantity]);

  const handleDecrement = useCallback(() => {
    if (quantity > 1) {
      updateQuantity(product.id, quantity - 1);
    } else {
      removeItem(product.id);
    }
  }, [product.id, quantity, updateQuantity, removeItem]);

  const handleRemove = useCallback(() => {
    removeItem(product.id);
  }, [product.id, removeItem]);

  return (
    <div className="flex gap-3 rounded-lg border border-border bg-card p-3">
      {/* Product Image */}
      <div className="h-20 w-20 flex-shrink-0 overflow-hidden rounded-md bg-muted">
        <img
          src={
            product.image_url ||
            `https://placehold.co/80x80/e2e8f0/64748b?text=${encodeURIComponent(product.name.slice(0, 5))}`
          }
          alt={product.name}
          className="h-full w-full object-cover"
          loading="lazy"
        />
      </div>

      {/* Product Info */}
      <div className="flex flex-1 flex-col">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="line-clamp-1 font-medium text-card-foreground">
              {product.name}
            </h3>
            <p className="text-sm text-muted-foreground">
              {formatPrice(product.price)}
            </p>
          </div>
          <button
            onClick={handleRemove}
            className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-destructive"
            aria-label="移除商品"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>

        {/* Quantity Controls & Total */}
        <div className="mt-2 flex items-center justify-between">
          {/* Quantity Selector */}
          <div className="flex items-center rounded-md border border-border">
            <button
              onClick={handleDecrement}
              className="px-3 py-1 text-lg hover:bg-accent disabled:opacity-50"
              aria-label="減少數量"
            >
              −
            </button>
            <span className="min-w-[2rem] text-center text-sm font-medium">
              {quantity}
            </span>
            <button
              onClick={handleIncrement}
              disabled={isMaxQuantity}
              className="px-3 py-1 text-lg hover:bg-accent disabled:opacity-50"
              aria-label="增加數量"
            >
              +
            </button>
          </div>

          {/* Item Total */}
          <span className="font-semibold text-primary">
            {formatPrice(itemTotal)}
          </span>
        </div>

        {/* Stock Warning */}
        {isMaxQuantity && (
          <p className="mt-1 text-xs text-destructive">已達最大庫存數量</p>
        )}
      </div>
    </div>
  );
}

export const CartItem = memo(CartItemComponent);
