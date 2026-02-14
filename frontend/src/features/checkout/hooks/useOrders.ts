/**
 * Order API Hooks.
 *
 * Ref: .blueprint/frontend_structure.md §4B
 *
 * Features:
 * - Place order mutation with error handling
 * - Coupon validation
 * - Rollback on conflict errors with affected product info
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import apiClient from '@/api/client';
import type {
  Coupon,
  PlaceOrderRequest,
  PlaceOrderResponse,
  UUID,
} from '@/types';
import { ApiErrorCode, getUserFriendlyErrorMessage, isApiError } from '@/types';

// =============================================================================
// Query Keys
// =============================================================================

export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (filters: Record<string, string>) =>
    [...orderKeys.lists(), filters] as const,
  details: () => [...orderKeys.all, 'detail'] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
};

export const couponKeys = {
  all: ['coupons'] as const,
  validate: (code: string) => [...couponKeys.all, 'validate', code] as const,
};

// =============================================================================
// API Functions
// =============================================================================

async function placeOrder(data: PlaceOrderRequest): Promise<PlaceOrderResponse> {
  // Debug log to see what's being sent
  console.log('PlaceOrder request data:', JSON.stringify(data, null, 2));
  const response = await apiClient.post<PlaceOrderResponse>('/orders/', data);
  return response.data;
}

async function validateCoupon(code: string, subtotal: number): Promise<Coupon> {
  const response = await apiClient.post<{ coupon: Coupon }>('/coupons/validate/', {
    code,
    subtotal,
  });
  return response.data.coupon;
}

// =============================================================================
// Error Handling
// =============================================================================

/**
 * Stock conflict detail for a specific product.
 */
export interface StockConflictItem {
  productId: UUID;
  productName?: string;
  requestedQuantity: number;
  availableStock: number;
}

/**
 * Extended order error with conflict details.
 */
export interface OrderError {
  code: string;
  message: string;
  isConflict: boolean;
  shouldRefreshStock: boolean;
  /** Affected products when stock conflict occurs */
  conflictItems: StockConflictItem[];
  /** Raw error details from backend */
  details?: Record<string, unknown>;
}

/**
 * Parse API error response into OrderError.
 */
export function parseOrderError(error: unknown): OrderError {
  const baseError: OrderError = {
    code: 'unknown_error',
    message: '發生未知錯誤，請稍後再試',
    isConflict: false,
    shouldRefreshStock: false,
    conflictItems: [],
  };

  if (!(error instanceof AxiosError) || !error.response?.data) {
    return baseError;
  }

  const data = error.response.data;
  const status = error.response.status;

  if (!isApiError(data)) {
    return baseError;
  }

  const code = data.error.code;
  const details = data.error.details as Record<string, unknown> | undefined;

  // Check if it's a conflict error (409)
  const isConflict =
    status === 409 ||
    code === ApiErrorCode.STOCK_CONFLICT ||
    code === ApiErrorCode.INSUFFICIENT_STOCK;

  // Should refresh stock data on conflict
  const shouldRefreshStock =
    code === ApiErrorCode.STOCK_CONFLICT ||
    code === ApiErrorCode.INSUFFICIENT_STOCK;

  // Extract conflict items from error details
  const conflictItems: StockConflictItem[] = [];

  if (isConflict && details) {
    // Backend may return affected items in details
    // Expected format: { items: [{ product_id, product_name, requested, available }] }
    const items = details.items as Array<{
      product_id?: string;
      product_name?: string;
      requested?: number;
      available?: number;
    }> | undefined;

    if (Array.isArray(items)) {
      items.forEach((item) => {
        if (item.product_id) {
          conflictItems.push({
            productId: item.product_id,
            productName: item.product_name,
            requestedQuantity: item.requested || 0,
            availableStock: item.available || 0,
          });
        }
      });
    }

    // Single item conflict
    if (details.product_id) {
      conflictItems.push({
        productId: details.product_id as string,
        productName: details.product_name as string | undefined,
        requestedQuantity: (details.requested as number) || 0,
        availableStock: (details.available as number) || 0,
      });
    }
  }

  // Custom message for stock conflicts
  let message = data.error.message || getUserFriendlyErrorMessage(code);
  if (isConflict && !data.error.message) {
    message = '有人比你快一步！部分商品庫存已不足';
  }

  return {
    code,
    message,
    isConflict,
    shouldRefreshStock,
    conflictItems,
    details,
  };
}

// =============================================================================
// Place Order Mutation
// =============================================================================

interface UsePlaceOrderOptions {
  onSuccess?: (data: PlaceOrderResponse) => void;
  onError?: (error: OrderError) => void;
  onConflict?: (error: OrderError) => void;
}

export function usePlaceOrder(options?: UsePlaceOrderOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: placeOrder,
    onSuccess: (data) => {
      // Invalidate orders list cache
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
      options?.onSuccess?.(data);
    },
    onError: (error: unknown) => {
      const orderError = parseOrderError(error);

      // Ref: frontend_structure.md §4B - Rollback on 409 Conflict
      if (orderError.shouldRefreshStock) {
        // Invalidate product queries to get latest stock/version
        queryClient.invalidateQueries({ queryKey: ['products'] });
        options?.onConflict?.(orderError);
      } else {
        options?.onError?.(orderError);
      }
    },
  });
}

// =============================================================================
// Validate Coupon Mutation
// =============================================================================

interface UseValidateCouponOptions {
  onSuccess?: (coupon: Coupon) => void;
  onError?: (message: string) => void;
}

export function useValidateCoupon(options?: UseValidateCouponOptions) {
  return useMutation({
    mutationFn: ({ code, subtotal }: { code: string; subtotal: number }) =>
      validateCoupon(code, subtotal),
    onSuccess: (coupon) => {
      options?.onSuccess?.(coupon);
    },
    onError: (error: unknown) => {
      const orderError = parseOrderError(error);
      options?.onError?.(orderError.message);
    },
  });
}
