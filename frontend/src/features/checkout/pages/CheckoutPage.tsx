/**
 * Checkout Page Component.
 *
 * Ref: .blueprint/frontend_structure.md §4B
 *
 * Features:
 * - Order summary display
 * - Coupon input and validation
 * - Place order with loading state
 * - 409 Conflict handling with StockConflictModal:
 *   - Toast: "有人比你快一步"
 *   - Auto-update stock state
 *   - Options: 返回購物車 / 移除失效商品 / 調整數量
 */

import { memo, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useCartStore, useCartItems, useCartSubtotal } from '@/store';
import { useAddToast } from '@/store/toastStore';
import type { Coupon, CouponMinimal, DeliverySlot, PlaceOrderResponse, UUID } from '@/types';
import { calculateDiscount } from '@/types';
import { formatPrice } from '@/utils';
import { usePlaceOrder, type OrderError } from '../hooks/useOrders';
import { CouponInput } from '../components/CouponInput';
import { DeliverySlotSelector } from '../components/DeliverySlotSelector';
import { OrderSummary } from '../components/OrderSummary';
import { StockConflictModal } from '../components/StockConflictModal';

interface CheckoutPageProps {
  onBack: () => void;
  onOrderComplete: (order: PlaceOrderResponse) => void;
}

function CheckoutPageComponent({ onBack, onOrderComplete }: CheckoutPageProps) {
  const queryClient = useQueryClient();
  const items = useCartItems();
  const subtotal = useCartSubtotal();
  const clearCart = useCartStore((state) => state.clearCart);
  const removeItem = useCartStore((state) => state.removeItem);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const addToast = useAddToast();

  const [appliedCoupon, setAppliedCoupon] = useState<Coupon | null>(null);
  const [selectedDeliverySlot, setSelectedDeliverySlot] = useState<DeliverySlot | null>(null);
  const [conflictError, setConflictError] = useState<OrderError | null>(null);
  const [showConflictModal, setShowConflictModal] = useState(false);

  // Calculate totals
  const discount = appliedCoupon
    ? calculateDiscount(appliedCoupon as CouponMinimal, subtotal)
    : 0;
  const total = subtotal - discount;

  // Place order mutation
  const placeOrderMutation = usePlaceOrder({
    onSuccess: (data) => {
      addToast({
        type: 'success',
        message: '訂單建立成功！請在 15 分鐘內完成付款。',
      });
      clearCart();
      onOrderComplete(data);
    },
    onConflict: (error: OrderError) => {
      // Ref: frontend_structure.md §4B - Rollback on 409 Conflict
      // 1. Show toast "有人比你快一步"
      addToast({
        type: 'error',
        message: '有人比你快一步！部分商品庫存已不足',
        duration: 5000,
      });

      // 2. Auto-update stock (done by invalidateQueries in usePlaceOrder)
      // Force immediate refetch
      queryClient.refetchQueries({ queryKey: ['products'] });

      // 3. Show conflict modal with options
      setConflictError(error);
      setShowConflictModal(true);
    },
    onError: (error: OrderError) => {
      addToast({
        type: 'error',
        message: error.message,
      });
    },
  });

  // Handle place order
  const handlePlaceOrder = useCallback(() => {
    if (items.length === 0) {
      addToast({
        type: 'warning',
        message: '購物車是空的',
      });
      return;
    }

    if (!selectedDeliverySlot) {
      addToast({
        type: 'warning',
        message: '請選擇配送時段',
      });
      return;
    }

    // Normalize product IDs to valid UUID format
    const normalizedItems = items.map((item) => {
      const id = String(item.product_id);

      // Check if it's a valid UUID (hex digits only)
      const isValidUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);

      let normalizedId = id;
      if (!isValidUUID) {
        // Convert invalid IDs to a test UUID (v5 style based on the original ID)
        // Replace non-hex characters with hex equivalents
        const cleanId = id.toLowerCase()
          .replace(/[^0-9a-f-]/g, (char) => {
            // Convert letters to their hex position in alphabet (a=1, b=2...)
            if (char >= 'a' && char <= 'f') return char;
            if (char >= 'g' && char <= 'z') {
              const val = char.charCodeAt(0) - 'a'.charCodeAt(0) + 1;
              return (val % 16).toString(16);
            }
            return '0';
          });

        // Pad to 32 characters and format as UUID
        const padded = cleanId.replace(/-/g, '').padEnd(32, '0').substring(0, 32);
        normalizedId = [
          padded.substring(0, 8),
          padded.substring(8, 12),
          '5' + padded.substring(13, 16), // Version 5
          '8' + padded.substring(17, 20), // Variant
          padded.substring(20, 32)
        ].join('-');
      }

      return {
        product_id: normalizedId,
        quantity: item.quantity,
      };
    });

    console.log('Original items:', items);
    console.log('Normalized items:', normalizedItems);

    // Clear any previous conflict error
    setConflictError(null);

    // Ref: frontend_structure.md §4B - Button enters loading state
    placeOrderMutation.mutate({
      items: normalizedItems,
      coupon_code: appliedCoupon?.code,
      delivery_slot_id: selectedDeliverySlot.id,
    });
  }, [items, appliedCoupon, selectedDeliverySlot, placeOrderMutation, addToast]);

  // Handle coupon
  const handleApplyCoupon = useCallback((coupon: Coupon) => {
    setAppliedCoupon(coupon);
  }, []);

  const handleRemoveCoupon = useCallback(() => {
    setAppliedCoupon(null);
  }, []);

  // Handle delivery slot selection
  const handleSlotSelect = useCallback((slot: DeliverySlot) => {
    setSelectedDeliverySlot(slot);
  }, []);

  // Conflict modal handlers
  const handleCloseConflictModal = useCallback(() => {
    setShowConflictModal(false);
  }, []);

  const handleReturnToCart = useCallback(() => {
    setShowConflictModal(false);
    onBack();
  }, [onBack]);

  const handleRemoveUnavailable = useCallback(
    (productIds: UUID[]) => {
      productIds.forEach((id) => removeItem(id));
      addToast({
        type: 'info',
        message: `已移除 ${productIds.length} 件失效商品`,
      });
    },
    [removeItem, addToast]
  );

  const handleUpdateQuantities = useCallback(
    (updates: Array<{ productId: UUID; quantity: number }>) => {
      updates.forEach(({ productId, quantity }) => {
        updateQuantity(productId, quantity);
      });
      addToast({
        type: 'success',
        message: '已調整商品數量，請重新確認訂單',
      });
    },
    [updateQuantity, addToast]
  );

  // Empty cart state
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
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
        <h2 className="mb-2 text-xl font-semibold text-foreground">
          購物車是空的
        </h2>
        <p className="mb-4 text-muted-foreground">
          請先將商品加入購物車再結帳
        </p>
        <button
          onClick={onBack}
          className="rounded-md bg-primary px-6 py-2 font-medium text-primary-foreground hover:bg-primary/90"
        >
          繼續購物
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6 flex items-center gap-4">
          <button
            onClick={onBack}
            className="rounded-md p-2 hover:bg-accent"
            aria-label="返回"
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
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
          <h1 className="text-2xl font-bold text-foreground">結帳</h1>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left: Coupon & Info */}
          <div className="space-y-6">
            {/* Coupon Section */}
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="mb-4 font-semibold text-card-foreground">優惠碼</h3>
              <CouponInput
                subtotal={subtotal}
                appliedCoupon={appliedCoupon}
                onApply={handleApplyCoupon}
                onRemove={handleRemoveCoupon}
              />
            </div>

            {/* Delivery Slot Section */}
            <div className="rounded-lg border border-border bg-card p-4">
              <DeliverySlotSelector
                selectedSlot={selectedDeliverySlot}
                onSlotSelect={handleSlotSelect}
              />
            </div>

            {/* Stock Conflict Warning (inline fallback) */}
            {placeOrderMutation.isError && conflictError?.isConflict && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                <div className="flex gap-3">
                  <svg
                    className="h-5 w-5 flex-shrink-0 text-red-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <div className="flex-1">
                    <p className="font-semibold text-red-800">
                      庫存衝突
                    </p>
                    <p className="mt-1 text-sm text-red-700">
                      {conflictError.message}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        onClick={() => setShowConflictModal(true)}
                        className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                      >
                        查看詳情
                      </button>
                      <button
                        onClick={onBack}
                        className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100"
                      >
                        返回購物車
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* General Error Warning */}
            {placeOrderMutation.isError && !conflictError?.isConflict && (
              <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                <div className="flex gap-3">
                  <svg
                    className="h-5 w-5 flex-shrink-0 text-yellow-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <div>
                    <p className="font-medium text-yellow-800">下單失敗</p>
                    <p className="mt-1 text-sm text-yellow-700">
                      請稍後再試，或聯繫客服協助。
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Payment Info */}
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="mb-2 font-semibold text-card-foreground">
                付款說明
              </h3>
              <p className="text-sm text-muted-foreground">
                訂單建立後，您將有 15 分鐘的時間完成付款。
                超過時間後庫存將自動釋放，訂單將被取消。
              </p>
            </div>

            {/* Real-time Stock Notice */}
            <div className="flex items-center gap-2 rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
              </span>
              庫存資訊即時更新中
            </div>
          </div>

          {/* Right: Order Summary */}
          <div className="space-y-4">
            <OrderSummary
              items={items}
              subtotal={subtotal}
              appliedCoupon={appliedCoupon}
              deliverySlot={selectedDeliverySlot}
            />

            {/* Place Order Button */}
            <button
              onClick={handlePlaceOrder}
              disabled={placeOrderMutation.isPending || items.length === 0}
              className="w-full rounded-lg bg-primary py-4 text-lg font-semibold text-primary-foreground shadow-lg transition-all hover:bg-primary/90 hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
            >
              {placeOrderMutation.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <svg
                    className="h-5 w-5 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  處理中...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  確認下單 {formatPrice(total)}
                </span>
              )}
            </button>

            {/* Retry hint after error */}
            {placeOrderMutation.isError && (
              <p className="text-center text-sm text-muted-foreground">
                庫存已更新，您可以重新嘗試下單
              </p>
            )}

            {/* Security Note */}
            <p className="text-center text-xs text-muted-foreground">
              <svg
                className="mr-1 inline-block h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
              安全加密付款
            </p>
          </div>
        </div>
      </div>

      {/* Stock Conflict Modal */}
      <StockConflictModal
        isOpen={showConflictModal}
        conflictItems={conflictError?.conflictItems || []}
        cartItems={items}
        onClose={handleCloseConflictModal}
        onReturnToCart={handleReturnToCart}
        onRemoveUnavailable={handleRemoveUnavailable}
        onUpdateQuantities={handleUpdateQuantities}
      />
    </>
  );
}

export const CheckoutPage = memo(CheckoutPageComponent);
