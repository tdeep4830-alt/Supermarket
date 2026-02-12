/**
 * API Response & Error Types.
 *
 * Ref: .blueprint/protocol.md §4
 */

// =============================================================================
// API Error Types
// =============================================================================

export const ApiErrorCode = {
  INSUFFICIENT_STOCK: 'insufficient_stock',
  STOCK_CONFLICT: 'stock_conflict',
  ORDER_NOT_FOUND: 'order_not_found',
  INVALID_ORDER_STATUS: 'invalid_order_status',
  COUPON_NOT_FOUND: 'coupon_not_found',
  COUPON_EXPIRED: 'coupon_expired',
  COUPON_ALREADY_USED: 'coupon_already_used',
  COUPON_QUOTA_EXCEEDED: 'coupon_quota_exceeded',
  MINIMUM_PURCHASE_NOT_MET: 'minimum_purchase_not_met',
  RATE_LIMIT_EXCEEDED: 'rate_limit_exceeded',
  VALIDATION_ERROR: 'validation_error',
  NOT_FOUND: 'not_found',
  UNAUTHORIZED: 'unauthorized',
  FORBIDDEN: 'forbidden',
} as const;

export type ApiErrorCode = (typeof ApiErrorCode)[keyof typeof ApiErrorCode];

export interface ApiError {
  error: {
    code: ApiErrorCode | string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface ValidationErrorDetails {
  [field: string]: string[];
}

// =============================================================================
// API Response Helpers
// =============================================================================

export function isApiError(response: unknown): response is ApiError {
  return (
    typeof response === 'object' &&
    response !== null &&
    'error' in response &&
    typeof (response as ApiError).error === 'object'
  );
}

export function getErrorMessage(error: ApiError): string {
  return error.error.message;
}

export function getUserFriendlyErrorMessage(code: ApiErrorCode | string): string {
  const messages: Record<string, string> = {
    [ApiErrorCode.INSUFFICIENT_STOCK]: '庫存不足，請減少數量或選擇其他商品',
    [ApiErrorCode.STOCK_CONFLICT]: '有人比你快一步，請重試',
    [ApiErrorCode.COUPON_NOT_FOUND]: '優惠碼不存在',
    [ApiErrorCode.COUPON_EXPIRED]: '優惠碼已過期',
    [ApiErrorCode.COUPON_ALREADY_USED]: '您已使用過此優惠碼',
    [ApiErrorCode.COUPON_QUOTA_EXCEEDED]: '優惠碼已被搶光',
    [ApiErrorCode.MINIMUM_PURCHASE_NOT_MET]: '未達最低消費金額',
    [ApiErrorCode.RATE_LIMIT_EXCEEDED]: '操作太頻繁，請稍後再試',
    [ApiErrorCode.ORDER_NOT_FOUND]: '訂單不存在',
  };
  return messages[code] || '發生錯誤，請稍後再試';
}

export function httpStatusToErrorCode(status: number): ApiErrorCode | null {
  switch (status) {
    case 401:
      return ApiErrorCode.UNAUTHORIZED;
    case 403:
      return ApiErrorCode.FORBIDDEN;
    case 404:
      return ApiErrorCode.NOT_FOUND;
    case 429:
      return ApiErrorCode.RATE_LIMIT_EXCEEDED;
    default:
      return null;
  }
}
