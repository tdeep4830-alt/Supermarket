/**
 * Stock Conflict Modal Component.
 *
 * Ref: .blueprint/frontend_structure.md §4B
 *
 * Displays when order fails due to stock conflict (409).
 * Shows affected products and provides resolution options:
 * - Return to cart
 * - Remove unavailable items
 * - Update quantities to available stock
 */

import { memo, useCallback, useMemo } from 'react';
import type { CartItem, UUID } from '@/types';
import { formatPrice } from '@/utils';
import type { StockConflictItem } from '../hooks/useOrders';

interface StockConflictModalProps {
  isOpen: boolean;
  conflictItems: StockConflictItem[];
  cartItems: CartItem[];
  onClose: () => void;
  onReturnToCart: () => void;
  onRemoveUnavailable: (productIds: UUID[]) => void;
  onUpdateQuantities: (updates: Array<{ productId: UUID; quantity: number }>) => void;
}

function StockConflictModalComponent({
  isOpen,
  conflictItems,
  cartItems,
  onClose,
  onReturnToCart,
  onRemoveUnavailable,
  onUpdateQuantities,
}: StockConflictModalProps) {
  // Match conflict items with cart items for display
  const affectedItems = useMemo(() => {
    return conflictItems.map((conflict) => {
      const cartItem = cartItems.find(
        (item) => item.product_id === conflict.productId
      );
      return {
        ...conflict,
        cartItem,
        productName: conflict.productName || cartItem?.product.name || '未知商品',
        imageUrl: cartItem?.product.image_url,
        price: cartItem?.product.price,
        isSoldOut: conflict.availableStock === 0,
        canAdjust: conflict.availableStock > 0,
      };
    });
  }, [conflictItems, cartItems]);

  // Items that are completely sold out
  const soldOutItems = useMemo(
    () => affectedItems.filter((item) => item.isSoldOut),
    [affectedItems]
  );

  // Items that can be adjusted
  const adjustableItems = useMemo(
    () => affectedItems.filter((item) => item.canAdjust),
    [affectedItems]
  );

  // Handle remove all unavailable
  const handleRemoveUnavailable = useCallback(() => {
    const productIds = soldOutItems.map((item) => item.productId);
    onRemoveUnavailable(productIds);
    onClose();
  }, [soldOutItems, onRemoveUnavailable, onClose]);

  // Handle adjust quantities
  const handleAdjustQuantities = useCallback(() => {
    const updates = adjustableItems.map((item) => ({
      productId: item.productId,
      quantity: item.availableStock,
    }));
    onUpdateQuantities(updates);

    // Also remove sold out items
    if (soldOutItems.length > 0) {
      const productIds = soldOutItems.map((item) => item.productId);
      onRemoveUnavailable(productIds);
    }

    onClose();
  }, [adjustableItems, soldOutItems, onUpdateQuantities, onRemoveUnavailable, onClose]);

  // Handle return to cart
  const handleReturnToCart = useCallback(() => {
    onReturnToCart();
    onClose();
  }, [onReturnToCart, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-4 flex items-start gap-3">
          <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100">
            <svg
              className="h-6 w-6 text-red-600"
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
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">
              有人比你快一步！
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              以下商品庫存已變更，請選擇處理方式
            </p>
          </div>
        </div>

        {/* Affected Items List */}
        <div className="mb-6 max-h-64 overflow-y-auto rounded-lg border border-gray-200">
          {affectedItems.map((item) => (
            <div
              key={item.productId}
              className={`flex items-center gap-3 border-b border-gray-100 p-3 last:border-b-0 ${
                item.isSoldOut ? 'bg-red-50' : 'bg-yellow-50'
              }`}
            >
              {/* Product Image */}
              <div className="h-14 w-14 flex-shrink-0 overflow-hidden rounded-lg bg-gray-100">
                {item.imageUrl ? (
                  <img
                    src={item.imageUrl}
                    alt={item.productName}
                    className={`h-full w-full object-cover ${
                      item.isSoldOut ? 'grayscale' : ''
                    }`}
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-gray-400">
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                )}
              </div>

              {/* Product Info */}
              <div className="flex-1 min-w-0">
                <p className="truncate font-medium text-gray-900">
                  {item.productName}
                </p>
                {item.price && (
                  <p className="text-sm text-gray-500">{formatPrice(item.price)}</p>
                )}
              </div>

              {/* Stock Status */}
              <div className="flex-shrink-0 text-right">
                {item.isSoldOut ? (
                  <div className="rounded-full bg-red-100 px-3 py-1">
                    <span className="text-sm font-semibold text-red-700">
                      已售罄
                    </span>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-xs text-gray-500 line-through">
                      需要 {item.requestedQuantity} 件
                    </p>
                    <div className="rounded-full bg-yellow-100 px-3 py-1">
                      <span className="text-sm font-semibold text-yellow-700">
                        僅剩 {item.availableStock} 件
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="space-y-3">
          {/* Primary Action - Adjust and Continue */}
          {adjustableItems.length > 0 && (
            <button
              onClick={handleAdjustQuantities}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary py-3 font-semibold text-white transition-colors hover:bg-primary/90"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              調整數量並繼續結帳
            </button>
          )}

          {/* Remove Unavailable Items */}
          {soldOutItems.length > 0 && adjustableItems.length === 0 && (
            <button
              onClick={handleRemoveUnavailable}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-600 py-3 font-semibold text-white transition-colors hover:bg-red-700"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
              移除失效商品 ({soldOutItems.length})
            </button>
          )}

          {/* Return to Cart */}
          <button
            onClick={handleReturnToCart}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white py-3 font-semibold text-gray-700 transition-colors hover:bg-gray-50"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            返回購物車
          </button>

          {/* Cancel */}
          <button
            onClick={onClose}
            className="w-full py-2 text-sm text-gray-500 hover:text-gray-700"
          >
            稍後處理
          </button>
        </div>

        {/* Help Text */}
        <p className="mt-4 text-center text-xs text-gray-400">
          庫存資訊已自動更新，您可以重新選擇商品數量
        </p>
      </div>
    </>
  );
}

export const StockConflictModal = memo(StockConflictModalComponent);
