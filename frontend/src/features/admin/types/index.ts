/**
 * Admin Portal Type Definitions.
 */

export interface InventoryItem {
  id: string;
  name: string;
  price: string;
  category: {
    id: string;
    name: string;
  };
  stock: number;
  status: 'low_stock' | 'out_of_stock' | 'in_stock';
  created_at: string;
}

export interface OrderItem {
  id: string;
  user: {
    id: string;
    username: string;
    email: string;
  };
  status: 'PENDING' | 'PAID' | 'SHIPPED' | 'CANCELLED' | 'REFUNDED';
  total_amount: string;
  discount_amount: string;
  applied_coupon: string | null;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface RestockResponse {
  success: boolean;
  message: string;
  data: {
    product_id: string;
    quantity_added: number;
    old_quantity: number;
    new_quantity: number;
    updated_at: string;
  };
}

export interface RestockVariables {
  productId: string;
  quantity: number;
}

export interface PaginationMetadata {
  current_page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface AdminOrdersResponse {
  orders: OrderItem[];
  pagination: PaginationMetadata;
}
