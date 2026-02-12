/**
 * Order TypeScript Interfaces.
 *
 * Ref: .blueprint/data.md §1C
 * Ref: Backend serializers - apps/orders/serializers.py
 */

import type { DecimalString, ISODateTime, UUID } from './common';
import type { CouponMinimal } from './coupon';
import type { ProductMinimal } from './product';

// =============================================================================
// Order Status Enum
// =============================================================================

export const OrderStatus = {
  PENDING: 'PENDING',
  PAID: 'PAID',
  SHIPPED: 'SHIPPED',
  CANCELLED: 'CANCELLED',
  REFUNDED: 'REFUNDED',
} as const;

export type OrderStatus = (typeof OrderStatus)[keyof typeof OrderStatus];

export const OrderStatusConfig: Record<
  OrderStatus,
  { label: string; color: string }
> = {
  PENDING: { label: '待付款', color: 'yellow' },
  PAID: { label: '已付款', color: 'green' },
  SHIPPED: { label: '已發貨', color: 'blue' },
  CANCELLED: { label: '已取消', color: 'gray' },
  REFUNDED: { label: '已退款', color: 'red' },
};

// =============================================================================
// Order Item Types
// =============================================================================

export interface OrderItemInput {
  product_id: UUID;
  quantity: number;
}

export interface OrderItem {
  id: UUID;
  product: ProductMinimal;
  quantity: number;
  price_at_purchase: DecimalString;
  subtotal: DecimalString;
}

// =============================================================================
// Order Types
// =============================================================================

export interface Order {
  id: UUID;
  status: OrderStatus;
  total_amount: DecimalString;
  discount_amount: DecimalString;
  applied_coupon: CouponMinimal | null;
  items_count: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface OrderDetail {
  id: UUID;
  status: OrderStatus;
  total_amount: DecimalString;
  discount_amount: DecimalString;
  applied_coupon: CouponMinimal | null;
  payment_id: string;
  items: OrderItem[];
  subtotal: DecimalString;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

// =============================================================================
// Request/Response Types
// =============================================================================

export interface PlaceOrderRequest {
  items: OrderItemInput[];
  coupon_code?: string;
}

export interface PlaceOrderResponse {
  message: string;
  order: OrderDetail;
}

export interface OrdersListResponse {
  orders: Order[];
}

// =============================================================================
// Order Lock Timer (Ref: frontend_structure.md §4C)
// =============================================================================

export const ORDER_LOCK_TIMEOUT_MINUTES = 15;
export const ORDER_LOCK_TIMEOUT_MS = ORDER_LOCK_TIMEOUT_MINUTES * 60 * 1000;

export function calculateOrderLockRemaining(createdAt: string): number {
  const created = new Date(createdAt).getTime();
  const expires = created + ORDER_LOCK_TIMEOUT_MS;
  return Math.max(0, expires - Date.now());
}

export function isOrderLockExpired(createdAt: string): boolean {
  return calculateOrderLockRemaining(createdAt) === 0;
}
