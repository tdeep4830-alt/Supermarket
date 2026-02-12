/**
 * Admin Inventory Hooks.
 *
 * React Query hooks for admin inventory management.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../api/client';
import { showToast } from '../../../store/toastStore';
import { logger } from '../../../utils/logger';

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

/**
 * Hook to fetch admin inventory list.
 */
export function useAdminInventory(search?: string, status?: string) {
  return useQuery({
    queryKey: ['admin-inventory', search, status],
    queryFn: async (): Promise<InventoryItem[]> => {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (status) params.append('status', status);

      const response = await apiClient.get(
        `/admin/inventory/${params.toString() ? `?${params.toString()}` : ''}`
      );
      return response.data.inventory;
    },
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 30 * 1000, // Auto-refresh every 30 seconds for real-time stock
  });
}

/**
 * Hook to restock product.
 */
export function useRestockProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ productId, quantity }: RestockVariables): Promise<RestockResponse> => {
      const response = await apiClient.patch(`/admin/inventory/${productId}/restock/`, {
        quantity,
      });
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate and refetch inventory list
      queryClient.invalidateQueries({ queryKey: ['admin-inventory'] });

      showToast({
        type: 'success',
        title: 'Restock Successful',
        message: `Added ${data.data.quantity_added} units to ${data.data.new_quantity - data.data.quantity_added} → ${data.data.new_quantity}`,
      });

      logger.info('Product restocked', {
        productId: data.data.product_id,
        quantity: data.data.quantity_added,
        newStock: data.data.new_quantity,
      });
    },
    onError: (error: any) => {
      const message = error.response?.data?.error?.message || 'Failed to restock product';

      showToast({
        type: 'error',
        title: 'Restock Failed',
        message,
      });

      logger.error('Restock failed', { error: error.message });
    },
  });
}
