/**
 * Products Query Hooks.
 *
 * Ref: .blueprint/frontend_structure.md §4A
 * - staleTime: 2000 (2 seconds) for flash sale real-time updates
 * - refetchOnWindowFocus: true
 */

import { useQuery } from '@tanstack/react-query';
import { getProductById, getProducts } from '@/api/products';
import type { ProductWithStock, UUID } from '@/types';

// Query keys for cache management
export const productKeys = {
  all: ['products'] as const,
  lists: () => [...productKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) =>
    [...productKeys.lists(), filters] as const,
  details: () => [...productKeys.all, 'detail'] as const,
  detail: (id: UUID) => [...productKeys.details(), id] as const,
};

/**
 * Hook to fetch all products with stock info.
 * Ref: frontend_structure.md §4A - Real-time stock updates
 */
export function useProducts() {
  return useQuery<ProductWithStock[], Error>({
    queryKey: productKeys.lists(),
    queryFn: getProducts,
    staleTime: 2000, // Ref: frontend_structure.md §4A
    refetchOnWindowFocus: true,
    refetchInterval: 5000, // Auto-refresh every 5 seconds for flash sales
  });
}

/**
 * Hook to fetch single product with stock info.
 * Uses shorter staleTime for flash sale scenarios.
 */
export function useProduct(productId: UUID | undefined) {
  return useQuery<ProductWithStock, Error>({
    queryKey: productKeys.detail(productId!),
    queryFn: () => getProductById(productId!),
    enabled: !!productId,
    staleTime: 2000, // Refresh every 2 seconds for flash sales
    refetchOnWindowFocus: true,
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  });
}
