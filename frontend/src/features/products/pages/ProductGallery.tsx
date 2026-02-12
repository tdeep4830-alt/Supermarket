/**
 * Product Gallery Page.
 *
 * Ref: .blueprint/frontend_structure.md §4A
 *
 * Features:
 * - Category filtering
 * - Pagination
 * - Real-time stock updates via useStockFlash
 * - Responsive grid layout
 * - Loading skeletons
 */

import { memo, useState, useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useCartStore } from '@/store';
import type { Category, ProductWithStock } from '@/types';
import { useProducts, productKeys } from '../hooks';
import { ProductCardEnhanced } from '../components/ProductCardEnhanced';
import { ProductCardSkeleton } from '../components/ProductCardSkeleton';
import { CategoryFilter } from '../components/CategoryFilter';
import { Pagination, PageSizeSelector } from '../components/Pagination';

// =============================================================================
// Mock Categories (until backend is ready)
// =============================================================================

const MOCK_CATEGORIES: Category[] = [
  { id: 'cat-1', name: '新鮮水果', slug: 'fresh-fruits', parent: null, is_active: true },
  { id: 'cat-2', name: '肉類海鮮', slug: 'meat-seafood', parent: null, is_active: true },
  { id: 'cat-3', name: '乳製品', slug: 'dairy', parent: null, is_active: true },
  { id: 'cat-4', name: '烘焙麵包', slug: 'bakery', parent: null, is_active: true },
  { id: 'cat-5', name: '新鮮蔬菜', slug: 'vegetables', parent: null, is_active: true },
];

// =============================================================================
// Product Gallery Component
// =============================================================================

interface ProductGalleryProps {
  initialCategory?: string | null;
  initialPageSize?: number;
}

function ProductGalleryComponent({
  initialCategory = null,
  initialPageSize = 12,
}: ProductGalleryProps) {
  const queryClient = useQueryClient();
  const addToCart = useCartStore((state) => state.addItem);

  // State
  const [selectedCategory, setSelectedCategory] = useState<string | null>(initialCategory);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  // Fetch products
  const { data: allProducts, isLoading, isError, error, isFetching } = useProducts();

  // Filter products by category
  const filteredProducts = useMemo(() => {
    if (!allProducts) return [];
    if (!selectedCategory) return allProducts;
    return allProducts.filter(
      (product) => product.category.slug === selectedCategory
    );
  }, [allProducts, selectedCategory]);

  // Calculate product counts per category
  const productCounts = useMemo(() => {
    if (!allProducts) return {};
    return allProducts.reduce(
      (acc, product) => {
        const slug = product.category.slug;
        acc[slug] = (acc[slug] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );
  }, [allProducts]);

  // Paginate products
  const paginatedProducts = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredProducts.slice(startIndex, startIndex + pageSize);
  }, [filteredProducts, currentPage, pageSize]);

  const totalPages = Math.ceil(filteredProducts.length / pageSize);

  // Handlers
  const handleCategoryChange = useCallback((slug: string | null) => {
    setSelectedCategory(slug);
    setCurrentPage(1); // Reset to first page
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
    // Scroll to top of product grid
    window.scrollTo({ top: 200, behavior: 'smooth' });
  }, []);

  const handlePageSizeChange = useCallback((size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  }, []);

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: productKeys.all });
  }, [queryClient]);

  const handleAddToCart = useCallback(
    (product: ProductWithStock) => {
      addToCart(product, 1);
    },
    [addToCart]
  );

  // Error state
  if (isError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-8 text-center">
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
        <h3 className="mb-2 text-lg font-semibold text-red-800">載入商品失敗</h3>
        <p className="mb-4 text-red-600">{error?.message || '請稍後再試'}</p>
        <button
          onClick={handleRefresh}
          className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700"
        >
          重新載入
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">商品列表</h2>
          <p className="text-sm text-slate-500">
            {isFetching ? '更新中...' : `共 ${filteredProducts.length} 件商品`}
            {' · '}
            庫存每 5 秒自動更新
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isFetching}
          className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-50"
        >
          <svg
            className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          刷新庫存
        </button>
      </div>

      {/* Category Filter */}
      <CategoryFilter
        categories={MOCK_CATEGORIES}
        selectedCategory={selectedCategory}
        onSelect={handleCategoryChange}
        productCounts={productCounts}
      />

      {/* Product Grid */}
      {isLoading ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: pageSize }).map((_, i) => (
            <ProductCardSkeleton key={i} />
          ))}
        </div>
      ) : paginatedProducts.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-12 text-center">
          <svg
            className="mx-auto mb-4 h-12 w-12 text-slate-400"
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
          <h3 className="mb-2 text-lg font-semibold text-slate-700">
            此分類暫無商品
          </h3>
          <p className="text-slate-500">請選擇其他分類或稍後再來</p>
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {paginatedProducts.map((product) => (
            <ProductCardEnhanced
              key={product.id}
              product={product}
              onAddToCart={handleAddToCart}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex flex-col items-center gap-4 border-t border-slate-200 pt-6 sm:flex-row sm:justify-between">
          <PageSizeSelector
            pageSize={pageSize}
            onPageSizeChange={handlePageSizeChange}
          />
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        </div>
      )}

      {/* Real-time Update Indicator */}
      <div className="flex items-center justify-center gap-2 text-xs text-slate-400">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
        </span>
        即時庫存更新中
      </div>
    </div>
  );
}

export const ProductGallery = memo(ProductGalleryComponent);
