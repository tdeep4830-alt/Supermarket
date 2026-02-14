/**
 * Order Summary Component.
 *
 * Displays cart items and totals for checkout.
 */

import { memo } from 'react';
import type { CartItem, CouponMinimal, DeliverySlot } from '@/types';
import { calculateDiscount } from '@/types';
import { formatPrice } from '@/utils';

interface OrderSummaryProps {
  items: CartItem[];
  subtotal: number;
  appliedCoupon: CouponMinimal | null;
  deliverySlot?: DeliverySlot | null;
}

function OrderSummaryComponent({
  items,
  subtotal,
  appliedCoupon,
  deliverySlot,
}: OrderSummaryProps) {
  const discount = appliedCoupon ? calculateDiscount(appliedCoupon, subtotal) : 0;
  const total = subtotal - discount;

  return (
    <div className="rounded-lg border border-border bg-card">
      {/* Header */}
      <div className="border-b border-border px-4 py-3">
        <h3 className="font-semibold text-card-foreground">
          訂單摘要 ({items.length} 項商品)
        </h3>
      </div>

      {/* Items */}
      <div className="max-h-64 overflow-y-auto p-4">
        <ul className="space-y-3">
          {items.map((item) => {
            const itemTotal = parseFloat(item.product.price) * item.quantity;
            return (
              <li
                key={item.product_id}
                className="flex items-center gap-3"
              >
                {/* Thumbnail */}
                <div className="h-12 w-12 flex-shrink-0 overflow-hidden rounded-md bg-muted">
                  <img
                    src={
                      item.product.image_url ||
                      `https://placehold.co/48x48/e2e8f0/64748b?text=${encodeURIComponent(item.product.name.slice(0, 2))}`
                    }
                    alt={item.product.name}
                    className="h-full w-full object-cover"
                  />
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-card-foreground">
                    {item.product.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatPrice(item.product.price)} x {item.quantity}
                  </p>
                </div>

                {/* Price */}
                <span className="text-sm font-medium text-card-foreground">
                  {formatPrice(itemTotal)}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Totals */}
      <div className="border-t border-border p-4 space-y-2">
        {/* Subtotal */}
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">小計</span>
          <span className="text-card-foreground">{formatPrice(subtotal)}</span>
        </div>

        {/* Discount */}
        {discount > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-green-600">
              優惠折扣 ({appliedCoupon?.code})
            </span>
            <span className="text-green-600">-{formatPrice(discount)}</span>
          </div>
        )}

        {/* Delivery Slot */}
        {deliverySlot && (
          <>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">配送時段</span>
              <span className="text-card-foreground">
                {deliverySlot.date} {deliverySlot.start_time}
              </span>
            </div>
          </>
        )}

        {/* Divider */}
        <div className="my-2 border-t border-border" />

        {/* Total */}
        <div className="flex justify-between">
          <span className="font-semibold text-card-foreground">總計</span>
          <span className="text-xl font-bold text-primary">
            {formatPrice(total)}
          </span>
        </div>
      </div>
    </div>
  );
}

export const OrderSummary = memo(OrderSummaryComponent);
