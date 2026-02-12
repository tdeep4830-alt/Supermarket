/**
 * ProductCard Component.
 *
 * Ref: .blueprint/frontend_structure.md §3, §4A
 *
 * Features:
 * - Lazy loading images (loading="lazy")
 * - Skeleton placeholder while loading
 * - Low stock warning (< 10 items shows red)
 * - Stock progress bar
 * - React.memo for optimization
 */

import { memo, useState, useCallback } from 'react';
import type { ProductWithStock } from '@/types';
import { formatPrice } from '@/utils';

// Stock threshold for low stock warning
const LOW_STOCK_THRESHOLD = 10;

interface ProductCardProps {
  product: ProductWithStock;
  onAddToCart?: (product: ProductWithStock) => void;
}

/**
 * Stock indicator component showing remaining quantity.
 */
function StockIndicator({ stock }: { stock: number }) {
  const isLowStock = stock > 0 && stock <= LOW_STOCK_THRESHOLD;
  const isOutOfStock = stock === 0;

  if (isOutOfStock) {
    return (
      <div className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-500">
        已售罄
      </div>
    );
  }

  if (isLowStock) {
    return (
      <div className="rounded-full bg-red-100 px-3 py-1 text-sm font-semibold text-red-600">
        剩餘 {stock} 件
      </div>
    );
  }

  return (
    <div className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-600">
      有貨
    </div>
  );
}

/**
 * Stock progress bar showing inventory level.
 */
function StockProgressBar({
  stock,
  maxStock = 100,
}: {
  stock: number;
  maxStock?: number;
}) {
  const percentage = Math.min((stock / maxStock) * 100, 100);
  const isLowStock = stock > 0 && stock <= LOW_STOCK_THRESHOLD;
  const isOutOfStock = stock === 0;

  const barColor = isOutOfStock
    ? 'bg-gray-300'
    : isLowStock
      ? 'bg-red-500'
      : 'bg-green-500';

  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
      <div
        className={`h-full transition-all duration-300 ${barColor}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

/**
 * Image component with lazy loading and skeleton placeholder.
 * Ref: frontend_structure.md §3A - Lazy Loading & Blur-up effect
 */
function ProductImage({
  src,
  alt,
  isLoading,
}: {
  src: string;
  alt: string;
  isLoading: boolean;
}) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const handleLoad = useCallback(() => {
    setImageLoaded(true);
  }, []);

  const handleError = useCallback(() => {
    setImageError(true);
    setImageLoaded(true);
  }, []);

  // Placeholder fallback
  const placeholderUrl = `https://placehold.co/300x300/e2e8f0/64748b?text=${encodeURIComponent(alt.slice(0, 10))}`;

  return (
    <div className="relative aspect-square overflow-hidden bg-muted">
      {/* Skeleton placeholder */}
      {(!imageLoaded || isLoading) && (
        <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200" />
      )}

      {/* Actual image with lazy loading */}
      <img
        src={imageError ? placeholderUrl : src || placeholderUrl}
        alt={alt}
        loading="lazy" /* Ref: frontend_structure.md §3A */
        onLoad={handleLoad}
        onError={handleError}
        className={`h-full w-full object-cover transition-opacity duration-300 ${
          imageLoaded && !isLoading ? 'opacity-100' : 'opacity-0'
        }`}
      />
    </div>
  );
}

/**
 * ProductCard - Main component.
 * Wrapped with React.memo for optimization.
 * Ref: frontend_structure.md §3C - Memoization
 */
function ProductCardComponent({ product, onAddToCart }: ProductCardProps) {
  const [isAdding, setIsAdding] = useState(false);
  const isOutOfStock = product.stock === 0;
  const isLowStock = product.stock > 0 && product.stock <= LOW_STOCK_THRESHOLD;

  const handleAddToCart = useCallback(async () => {
    if (isOutOfStock || isAdding) return;

    setIsAdding(true);
    try {
      onAddToCart?.(product);
    } finally {
      // Simulate brief loading state for UX
      setTimeout(() => setIsAdding(false), 300);
    }
  }, [isOutOfStock, isAdding, onAddToCart, product]);

  return (
    <div
      className={`group overflow-hidden rounded-lg border bg-card shadow-sm transition-all hover:shadow-md ${
        isOutOfStock ? 'opacity-75' : ''
      }`}
    >
      {/* Product Image */}
      <div className="relative">
        <ProductImage
          src={product.image_url}
          alt={product.name}
          isLoading={false}
        />

        {/* Low stock badge overlay */}
        {isLowStock && (
          <div className="absolute left-2 top-2">
            <span className="rounded bg-red-500 px-2 py-1 text-xs font-bold text-white shadow">
              限量
            </span>
          </div>
        )}

        {/* Out of stock overlay */}
        {isOutOfStock && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <span className="rounded-lg bg-white px-4 py-2 text-lg font-bold text-gray-800">
              已售罄
            </span>
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="p-4">
        {/* Category */}
        <p className="mb-1 text-xs text-muted-foreground">
          {product.category.name}
        </p>

        {/* Name */}
        <h3 className="mb-2 line-clamp-2 min-h-[2.5rem] font-semibold text-card-foreground">
          {product.name}
        </h3>

        {/* Price */}
        <p className="mb-3 text-xl font-bold text-primary">
          {formatPrice(product.price)}
        </p>

        {/* Stock Progress Bar */}
        <div className="mb-3">
          <StockProgressBar stock={product.stock} />
        </div>

        {/* Stock Indicator & Add to Cart */}
        <div className="flex items-center justify-between gap-2">
          <StockIndicator stock={product.stock} />

          <button
            onClick={handleAddToCart}
            disabled={isOutOfStock || isAdding}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              isOutOfStock
                ? 'cursor-not-allowed bg-gray-200 text-gray-400'
                : isAdding
                  ? 'bg-primary/70 text-primary-foreground'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90'
            }`}
          >
            {isAdding ? (
              <span className="flex items-center gap-1">
                <svg
                  className="h-4 w-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
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
                加入中
              </span>
            ) : isOutOfStock ? (
              '缺貨'
            ) : (
              '加入購物車'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Export memoized component
// Ref: frontend_structure.md §3C - Memoization
export const ProductCard = memo(ProductCardComponent);
