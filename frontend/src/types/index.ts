/**
 * Type Definitions Index.
 *
 * Re-exports all TypeScript interfaces for convenient importing.
 */

// Common types
export type {
  DecimalString,
  ISODateTime,
  PaginatedResponse,
  PaginationMeta,
  UUID,
} from './common';

// Product types
export type {
  Category,
  CategoryNested,
  Product,
  ProductMinimal,
  ProductWithStock,
  StockStatus,
} from './product';
export { calculateStockStatus } from './product';

// Coupon types
export type { Coupon, CouponMinimal } from './coupon';
export {
  calculateDiscount,
  DiscountType,
  formatDiscountText,
  isCouponValid,
} from './coupon';

// Order types
export type {
  Order,
  OrderDetail,
  OrderItem,
  OrderItemInput,
  OrdersListResponse,
  PlaceOrderRequest,
  PlaceOrderResponse,
} from './order';
export {
  calculateOrderLockRemaining,
  isOrderLockExpired,
  ORDER_LOCK_TIMEOUT_MINUTES,
  ORDER_LOCK_TIMEOUT_MS,
  OrderStatus,
  OrderStatusConfig,
} from './order';

// Cart types
export type {
  CartActions,
  CartComputed,
  CartItem,
  CartItemApi,
  CartState,
} from './cart';
export {
  calculateCartTotals,
  getCartItem,
  isInCart,
  validateCartQuantity,
} from './cart';

// API types
export type { ApiError, ValidationErrorDetails } from './api';
export {
  ApiErrorCode,
  getErrorMessage,
  getUserFriendlyErrorMessage,
  httpStatusToErrorCode,
  isApiError,
} from './api';

// User & Auth types
export type {
  CSRFResponse,
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  MembershipTier,
  RegisterRequest,
  RegisterResponse,
  User,
} from './user';
