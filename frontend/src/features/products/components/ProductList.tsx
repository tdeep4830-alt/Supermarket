/**
 * ProductList Component.
 *
 * Ref: .blueprint/frontend_structure.md §4A
 *
 * Features:
 * - React Query for data fetching with periodic refresh
 * - Loading skeletons
 * - Error handling
 * - Empty state
 * - Zustand cart integration
 */

import { useCallback } from 'react';
import type { ProductWithStock } from '@/types';
import { useCartStore } from '@/store';
import { useProducts } from '../hooks';
import { ProductCard } from './ProductCard';
import { ProductCardSkeleton } from './ProductCardSkeleton';

export function ProductList() {
  const { data: products, isLoading, isError, error, refetch } = useProducts();
  const addItem = useCartStore((state) => state.addItem);

  const handleAddToCart = useCallback(
    (product: ProductWithStock) => {
      addItem(product, 1);
    },
    [addItem]
  );

  // Loading state - show skeletons
  if (isLoading) {
    return (
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <ProductCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <svg
          className="mx-auto mb-4 h-12 w-12 text-red-400"
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
        <h3 className="mb-2 text-lg font-semibold text-red-800">
          載入商品失敗
        </h3>
        <p className="mb-4 text-red-600">
          {error?.message || '無法連接伺服器，請稍後再試'}
        </p>
        <button
          onClick={() => refetch()}
          className="rounded-md bg-red-600 px-4 py-2 text-white hover:bg-red-700"
        >
          重新載入
        </button>
      </div>
    );
  }

  // Empty state
  if (!products || products.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center">
        <svg
          className="mx-auto mb-4 h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
        <h3 className="mb-2 text-lg font-semibold text-gray-700">
          目前沒有商品
        </h3>
        <p className="text-gray-500">請稍後再來查看</p>
      </div>
    );
  }

  // Products grid
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {products.map((product) => (
        <ProductCard
          key={product.id}
          product={product as ProductWithStock}
          onAddToCart={handleAddToCart}
        />
      ))}
    </div>
  );
}
