/**
 * Coupon TypeScript Interfaces.
 *
 * Ref: .blueprint/data.md §1E
 * Ref: Backend serializers - apps/orders/serializers.py
 */

import type { DecimalString, ISODateTime, UUID } from './common';

// =============================================================================
// Discount Type Enum
// =============================================================================

export const DiscountType = {
  PERCENTAGE: 'PERCENTAGE',
  FIXED_AMOUNT: 'FIXED_AMOUNT',
} as const;

export type DiscountType = (typeof DiscountType)[keyof typeof DiscountType];

// =============================================================================
// Coupon Types
// =============================================================================

export interface Coupon {
  id: UUID;
  code: string;
  discount_type: DiscountType;
  discount_value: DecimalString;
  min_purchase_amount: DecimalString;
  valid_from: ISODateTime;
  valid_until: ISODateTime;
}

export interface CouponMinimal {
  code: string;
  discount_type: DiscountType;
  discount_value: DecimalString;
}

// =============================================================================
// Coupon Helpers
// =============================================================================

export function isCouponValid(coupon: Coupon): boolean {
  const now = new Date();
  const validFrom = new Date(coupon.valid_from);
  const validUntil = new Date(coupon.valid_until);
  return now >= validFrom && now <= validUntil;
}

export function calculateDiscount(
  coupon: CouponMinimal,
  subtotal: number
): number {
  const discountValue = parseFloat(coupon.discount_value);
  if (coupon.discount_type === DiscountType.PERCENTAGE) {
    return subtotal * (discountValue / 100);
  }
  return Math.min(discountValue, subtotal);
}

export function formatDiscountText(coupon: CouponMinimal): string {
  const value = parseFloat(coupon.discount_value);
  if (coupon.discount_type === DiscountType.PERCENTAGE) {
    return `${value}% OFF`;
  }
  return `$${value.toFixed(2)} OFF`;
}
