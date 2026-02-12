/**
 * Orders API Functions.
 *
 * Ref: Backend - apps/orders/views.py
 */

import type {
  Order,
  OrderDetail,
  OrdersListResponse,
  PlaceOrderRequest,
  PlaceOrderResponse,
  UUID,
} from '@/types';
import apiClient from './client';

/**
 * Place a new order.
 */
export async function placeOrder(
  data: PlaceOrderRequest
): Promise<PlaceOrderResponse> {
  const response = await apiClient.post<PlaceOrderResponse>('/orders/', data);
  return response.data;
}

/**
 * Get user's orders list.
 */
export async function getOrders(status?: string): Promise<Order[]> {
  const params = status ? { status } : undefined;
  const response = await apiClient.get<OrdersListResponse>('/orders/', {
    params,
  });
  return response.data.orders;
}

/**
 * Get order detail by ID.
 */
export async function getOrderById(orderId: UUID): Promise<OrderDetail> {
  const response = await apiClient.get<OrderDetail>(`/orders/${orderId}/`);
  return response.data;
}
