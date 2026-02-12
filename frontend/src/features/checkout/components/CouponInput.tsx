/**
 * Coupon Input Component.
 *
 * Ref: .blueprint/frontend_structure.md §4
 *
 * Features:
 * - Coupon code input with validation
 * - Visual feedback for valid/invalid coupons
 * - Discount preview
 */

import { memo, useCallback, useState } from 'react';
import type { Coupon, CouponMinimal } from '@/types';
import { calculateDiscount, formatDiscountText } from '@/types';
import { formatPrice } from '@/utils';
import { useValidateCoupon } from '../hooks/useOrders';

interface CouponInputProps {
  subtotal: number;
  appliedCoupon: Coupon | null;
  onApply: (coupon: Coupon) => void;
  onRemove: () => void;
}

function CouponInputComponent({
  subtotal,
  appliedCoupon,
  onApply,
  onRemove,
}: CouponInputProps) {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  const validateMutation = useValidateCoupon({
    onSuccess: (coupon) => {
      setError(null);
      setCode('');
      onApply(coupon);
    },
    onError: (message) => {
      setError(message);
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!code.trim()) {
        setError('請輸入優惠碼');
        return;
      }
      setError(null);
      validateMutation.mutate({ code: code.trim().toUpperCase(), subtotal });
    },
    [code, subtotal, validateMutation]
  );

  const handleRemove = useCallback(() => {
    setCode('');
    setError(null);
    onRemove();
  }, [onRemove]);

  // Show applied coupon
  if (appliedCoupon) {
    const discount = calculateDiscount(appliedCoupon as CouponMinimal, subtotal);

    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <p className="font-medium text-green-800">
                優惠碼已套用：{appliedCoupon.code}
              </p>
              <p className="text-sm text-green-600">
                {formatDiscountText(appliedCoupon as CouponMinimal)} - 折扣{' '}
                {formatPrice(discount)}
              </p>
            </div>
          </div>
          <button
            onClick={handleRemove}
            className="rounded p-1 text-green-700 hover:bg-green-100"
            aria-label="移除優惠碼"
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
      </div>
    );
  }

  // Show input form
  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={code}
            onChange={(e) => {
              setCode(e.target.value.toUpperCase());
              setError(null);
            }}
            placeholder="輸入優惠碼"
            className={`w-full rounded-md border px-4 py-2 text-sm ${
              error
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-border focus:border-primary focus:ring-primary'
            } focus:outline-none focus:ring-1`}
            disabled={validateMutation.isPending}
          />
          {validateMutation.isPending && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <svg
                className="h-4 w-4 animate-spin text-primary"
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
            </div>
          )}
        </div>
        <button
          type="submit"
          disabled={validateMutation.isPending || !code.trim()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          套用
        </button>
      </div>
      {error && (
        <p className="flex items-center gap-1 text-sm text-red-600">
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
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {error}
        </p>
      )}
    </form>
  );
}

export const CouponInput = memo(CouponInputComponent);
