/**
 * Order Success Page Component.
 *
 * Ref: .blueprint/frontend_structure.md §4C
 *
 * Features:
 * - Display order details from OrderDetailSerializer
 * - Final discount amount and coupon info
 * - Estimated delivery time
 * - 15-minute payment countdown timer
 * - Order status badge
 */

import { memo, useState, useEffect, useCallback, useMemo } from 'react';
import type { OrderDetail, PlaceOrderResponse } from '@/types';
import {
  OrderStatus,
  OrderStatusConfig,
  calculateOrderLockRemaining,
} from '@/types';
import { formatDiscountText } from '@/types';
import { formatPrice } from '@/utils';

// =============================================================================
// Types
// =============================================================================

interface OrderSuccessPageProps {
  orderResponse: PlaceOrderResponse;
  onContinueShopping: () => void;
  onPayNow?: () => void;
  onViewOrders?: () => void;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Calculate estimated delivery date (3-5 business days from order).
 */
function calculateEstimatedDelivery(orderDate: string): {
  earliest: Date;
  latest: Date;
} {
  const created = new Date(orderDate);

  // Add 3-5 business days
  const addBusinessDays = (date: Date, days: number): Date => {
    const result = new Date(date);
    let added = 0;
    while (added < days) {
      result.setDate(result.getDate() + 1);
      const dayOfWeek = result.getDay();
      if (dayOfWeek !== 0 && dayOfWeek !== 6) {
        added++;
      }
    }
    return result;
  };

  return {
    earliest: addBusinessDays(created, 3),
    latest: addBusinessDays(created, 5),
  };
}

/**
 * Format date range for display.
 */
function formatDateRange(earliest: Date, latest: Date): string {
  const options: Intl.DateTimeFormatOptions = {
    month: 'numeric',
    day: 'numeric',
    weekday: 'short',
  };

  const earliestStr = earliest.toLocaleDateString('zh-TW', options);
  const latestStr = latest.toLocaleDateString('zh-TW', options);

  return `${earliestStr} - ${latestStr}`;
}

/**
 * Format countdown time.
 */
function formatCountdown(ms: number): string {
  if (ms <= 0) return '已逾期';

  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);

  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// =============================================================================
// Sub-components
// =============================================================================

/**
 * Order Status Badge.
 */
function StatusBadge({ status }: { status: OrderStatus }) {
  const config = OrderStatusConfig[status];
  const colorClasses: Record<string, string> = {
    yellow: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    green: 'bg-green-100 text-green-800 border-green-200',
    blue: 'bg-blue-100 text-blue-800 border-blue-200',
    gray: 'bg-gray-100 text-gray-800 border-gray-200',
    red: 'bg-red-100 text-red-800 border-red-200',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium ${colorClasses[config.color]}`}
    >
      {config.label}
    </span>
  );
}

/**
 * Countdown Timer Component.
 */
function CountdownTimer({
  createdAt,
  onExpire,
}: {
  createdAt: string;
  onExpire?: () => void;
}) {
  const [remaining, setRemaining] = useState(() =>
    calculateOrderLockRemaining(createdAt)
  );

  useEffect(() => {
    const interval = setInterval(() => {
      const newRemaining = calculateOrderLockRemaining(createdAt);
      setRemaining(newRemaining);

      if (newRemaining <= 0) {
        clearInterval(interval);
        onExpire?.();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [createdAt, onExpire]);

  const isUrgent = remaining < 5 * 60 * 1000; // Less than 5 minutes
  const isExpired = remaining <= 0;

  if (isExpired) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex items-center justify-center gap-2 text-red-700">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="font-semibold">付款時間已過期</span>
        </div>
        <p className="mt-1 text-center text-sm text-red-600">
          訂單已自動取消，庫存已釋放
        </p>
      </div>
    );
  }

  return (
    <div
      className={`rounded-lg border p-4 ${
        isUrgent
          ? 'border-red-200 bg-red-50'
          : 'border-yellow-200 bg-yellow-50'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg
            className={`h-5 w-5 ${isUrgent ? 'text-red-600 animate-pulse' : 'text-yellow-600'}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className={`font-medium ${isUrgent ? 'text-red-800' : 'text-yellow-800'}`}>
            付款倒計時
          </span>
        </div>
        <span
          className={`font-mono text-2xl font-bold ${
            isUrgent ? 'text-red-600' : 'text-yellow-700'
          }`}
        >
          {formatCountdown(remaining)}
        </span>
      </div>
      <p className={`mt-2 text-sm ${isUrgent ? 'text-red-700' : 'text-yellow-700'}`}>
        {isUrgent ? '請盡快完成付款！' : '請在時間內完成付款，逾期訂單將自動取消'}
      </p>
    </div>
  );
}

/**
 * Order Item Row.
 */
function OrderItemRow({ item }: { item: OrderDetail['items'][0] }) {
  return (
    <div className="flex items-center gap-4 py-3">
      {/* Product Image */}
      <div className="h-16 w-16 flex-shrink-0 overflow-hidden rounded-lg bg-slate-100">
        {item.product.image_url ? (
          <img
            src={item.product.image_url}
            alt={item.product.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-slate-400">
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="flex-1 min-w-0">
        <p className="truncate font-medium text-slate-800">{item.product.name}</p>
        <p className="text-sm text-slate-500">
          {formatPrice(item.price_at_purchase)} x {item.quantity}
        </p>
      </div>

      {/* Subtotal */}
      <div className="text-right">
        <p className="font-semibold text-slate-800">{formatPrice(item.subtotal)}</p>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

function OrderSuccessPageComponent({
  orderResponse,
  onContinueShopping,
  onPayNow,
  onViewOrders,
}: OrderSuccessPageProps) {
  const { order } = orderResponse;
  const [isExpired, setIsExpired] = useState(false);

  // Calculate delivery estimate
  const deliveryEstimate = useMemo(
    () => calculateEstimatedDelivery(order.created_at),
    [order.created_at]
  );

  // Parse amounts
  const subtotal = parseFloat(order.subtotal);
  const discountAmount = parseFloat(order.discount_amount);
  const totalAmount = parseFloat(order.total_amount);
  const hasDiscount = discountAmount > 0;

  // Handle timer expiration
  const handleExpire = useCallback(() => {
    setIsExpired(true);
  }, []);

  // Handle payment
  const handlePayNow = useCallback(() => {
    if (onPayNow) {
      onPayNow();
    } else {
      // TODO: Navigate to payment gateway
      alert('前往付款頁面（尚未實作）');
    }
  }, [onPayNow]);

  return (
    <div className="mx-auto max-w-2xl">
      {/* Success Header */}
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
          <svg
            className="h-10 w-10 text-green-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h1 className="mb-2 text-2xl font-bold text-slate-800">訂單建立成功！</h1>
        <p className="text-slate-500">{orderResponse.message}</p>
      </div>

      {/* Order Info Card */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white shadow-sm">
        {/* Order Header */}
        <div className="border-b border-slate-100 px-6 py-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm text-slate-500">訂單編號</p>
              <p className="font-mono text-lg font-semibold text-slate-800">
                #{order.id.slice(0, 8).toUpperCase()}
              </p>
            </div>
            <StatusBadge status={order.status as OrderStatus} />
          </div>
          <p className="mt-2 text-sm text-slate-500">
            建立時間：{new Date(order.created_at).toLocaleString('zh-TW')}
          </p>
        </div>

        {/* Order Items */}
        <div className="border-b border-slate-100 px-6 py-2">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            訂單商品
          </h3>
          <div className="divide-y divide-slate-100">
            {order.items.map((item) => (
              <OrderItemRow key={item.id} item={item} />
            ))}
          </div>
        </div>

        {/* Price Summary */}
        <div className="px-6 py-4">
          <div className="space-y-2">
            {/* Subtotal */}
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">商品小計</span>
              <span className="text-slate-700">{formatPrice(subtotal)}</span>
            </div>

            {/* Discount */}
            {hasDiscount && (
              <div className="flex justify-between text-sm">
                <span className="flex items-center gap-2 text-green-600">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                    />
                  </svg>
                  優惠折扣
                  {order.applied_coupon && (
                    <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs font-medium">
                      {order.applied_coupon.code}
                    </span>
                  )}
                </span>
                <span className="font-medium text-green-600">
                  -{formatPrice(discountAmount)}
                </span>
              </div>
            )}

            {/* Coupon Details */}
            {order.applied_coupon && (
              <div className="flex justify-between text-xs text-slate-400">
                <span className="ml-6">
                  {formatDiscountText(order.applied_coupon)}
                </span>
              </div>
            )}

            {/* Divider */}
            <div className="my-2 border-t border-slate-200" />

            {/* Total */}
            <div className="flex justify-between">
              <span className="text-lg font-semibold text-slate-800">總計</span>
              <span className="text-2xl font-bold text-primary">
                {formatPrice(totalAmount)}
              </span>
            </div>

            {/* Savings */}
            {hasDiscount && (
              <p className="text-right text-sm text-green-600">
                已節省 {formatPrice(discountAmount)}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Payment Timer */}
      {order.status === OrderStatus.PENDING && (
        <div className="mb-6">
          <CountdownTimer createdAt={order.created_at} onExpire={handleExpire} />
        </div>
      )}

      {/* Delivery Estimate */}
      <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-blue-100">
            <svg
              className="h-5 w-5 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
              />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-blue-800">預計送達時間</p>
            <p className="text-lg font-medium text-blue-700">
              {formatDateRange(deliveryEstimate.earliest, deliveryEstimate.latest)}
            </p>
            <p className="mt-1 text-sm text-blue-600">
              付款完成後 3-5 個工作天內送達
            </p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-3">
        {/* Pay Now - Primary */}
        {order.status === OrderStatus.PENDING && !isExpired && (
          <button
            onClick={handlePayNow}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-4 text-lg font-semibold text-white shadow-lg transition-all hover:bg-primary/90 hover:shadow-xl"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
              />
            </svg>
            立即付款
          </button>
        )}

        {/* View Orders */}
        {onViewOrders && (
          <button
            onClick={onViewOrders}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-3 font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            查看訂單
          </button>
        )}

        {/* Continue Shopping */}
        <button
          onClick={onContinueShopping}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-3 font-medium text-slate-700 transition-colors hover:bg-slate-50"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
            />
          </svg>
          繼續購物
        </button>
      </div>

      {/* Order ID for reference */}
      <div className="mt-8 text-center">
        <p className="text-xs text-slate-400">
          完整訂單編號：{order.id}
        </p>
        {order.payment_id && (
          <p className="text-xs text-slate-400">付款編號：{order.payment_id}</p>
        )}
      </div>
    </div>
  );
}

export const OrderSuccessPage = memo(OrderSuccessPageComponent);
