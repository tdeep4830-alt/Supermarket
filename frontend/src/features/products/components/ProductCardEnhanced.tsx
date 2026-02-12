/**
 * Enhanced ProductCard Component with Real-time Stock Flash.
 *
 * Ref: .blueprint/frontend_structure.md §3, §4A
 *
 * Features:
 * - Real-time stock updates via useStockFlash
 * - Visual flash effect on stock changes
 * - Supermarket-style design (shadcn/ui inspired)
 * - Lazy loading images
 * - React.memo optimization
 */

import { memo, useState, useCallback } from 'react';
import type { ProductWithStock } from '@/types';
import { formatPrice } from '@/utils';
import {
  useStockFlash,
  getStockFlashClasses,
  getStockBadgeColor,
  getProgressBarColor,
} from '../hooks/useStockFlash';

interface ProductCardEnhancedProps {
  product: ProductWithStock;
  onAddToCart?: (product: ProductWithStock) => void;
}

/**
 * Stock Badge with flash animation.
 */
function StockBadge({
  stock,
  isFlashing,
  changeAmount,
  changeDirection,
  isCritical,
  isOutOfStock,
}: {
  stock: number;
  isFlashing: boolean;
  changeAmount: number;
  changeDirection: 'up' | 'down' | null;
  isCritical: boolean;
  isOutOfStock: boolean;
}) {
  const colors = getStockBadgeColor({
    stock,
    previousStock: null,
    isFlashing,
    changeDirection,
    changeAmount,
    isCritical,
    isOutOfStock,
    percentage: 0,
  });

  if (isOutOfStock) {
    return (
      <div className={`rounded-full px-3 py-1 text-sm font-medium ${colors.bg} ${colors.text}`}>
        售罄
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <div
        className={`rounded-full border px-3 py-1 text-sm font-medium transition-all ${colors.bg} ${colors.text} ${colors.border} ${
          isFlashing ? 'scale-110' : ''
        }`}
      >
        {isCritical ? `剩 ${stock} 件` : '有貨'}
      </div>

      {/* Stock change indicator */}
      {isFlashing && changeDirection && (
        <span
          className={`animate-bounce text-sm font-bold ${
            changeDirection === 'down' ? 'text-red-500' : 'text-green-500'
          }`}
        >
          {changeDirection === 'down' ? '-' : '+'}
          {changeAmount}
        </span>
      )}
    </div>
  );
}

/**
 * Animated Stock Progress Bar.
 */
function StockProgressBar({
  percentage,
  isFlashing,
  isCritical,
  isOutOfStock,
}: {
  percentage: number;
  isFlashing: boolean;
  isCritical: boolean;
  isOutOfStock: boolean;
}) {
  const barColor = getProgressBarColor({
    stock: 0,
    previousStock: null,
    isFlashing,
    changeDirection: null,
    changeAmount: 0,
    isCritical,
    isOutOfStock,
    percentage,
  });

  return (
    <div className="relative h-2 w-full overflow-hidden rounded-full bg-gray-100">
      <div
        className={`h-full transition-all duration-500 ease-out ${barColor} ${
          isFlashing && !isOutOfStock ? 'animate-pulse' : ''
        }`}
        style={{ width: `${percentage}%` }}
      />
      {/* Flash overlay */}
      {isFlashing && !isOutOfStock && (
        <div className="absolute inset-0 animate-ping bg-white/30" />
      )}
    </div>
  );
}

/**
 * Product Image with lazy loading and badges.
 */
function ProductImage({
  src,
  alt,
  isCritical,
  isOutOfStock,
  isFlashing,
}: {
  src: string;
  alt: string;
  isCritical: boolean;
  isOutOfStock: boolean;
  isFlashing: boolean;
}) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  const placeholder = `https://placehold.co/400x400/f1f5f9/64748b?text=${encodeURIComponent(
    alt.slice(0, 8)
  )}`;

  return (
    <div className="relative aspect-square overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Skeleton */}
      {!loaded && (
        <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-slate-100 via-slate-50 to-slate-100" />
      )}

      {/* Image */}
      <img
        src={error ? placeholder : src || placeholder}
        alt={alt}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        onError={() => {
          setError(true);
          setLoaded(true);
        }}
        className={`h-full w-full object-cover transition-all duration-300 ${
          loaded ? 'opacity-100' : 'opacity-0'
        } ${isOutOfStock ? 'grayscale' : ''} group-hover:scale-105`}
      />

      {/* Flash Sale Badge */}
      {isCritical && !isOutOfStock && (
        <div className="absolute left-0 top-3">
          <div className="flex items-center gap-1 bg-gradient-to-r from-red-500 to-orange-500 px-3 py-1 text-xs font-bold text-white shadow-lg">
            <svg className="h-3 w-3 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
              <path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" />
            </svg>
            限量搶購
          </div>
        </div>
      )}

      {/* Out of Stock Overlay */}
      {isOutOfStock && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-[2px]">
          <div className="rounded-lg bg-white px-6 py-3 text-lg font-bold text-gray-700 shadow-xl">
            已售罄
          </div>
        </div>
      )}

      {/* Flash Effect Overlay */}
      {isFlashing && !isOutOfStock && (
        <div className="pointer-events-none absolute inset-0 animate-ping bg-yellow-400/20" />
      )}
    </div>
  );
}

/**
 * ProductCardEnhanced - Main component with real-time stock updates.
 */
function ProductCardEnhancedComponent({
  product,
  onAddToCart,
}: ProductCardEnhancedProps) {
  const [isAdding, setIsAdding] = useState(false);

  // Real-time stock monitoring with flash effect
  const stockFlash = useStockFlash(product.stock, {
    maxStock: 100,
    flashDuration: 1500,
    criticalThreshold: 10,
  });

  const flashClasses = getStockFlashClasses(stockFlash);

  const handleAddToCart = useCallback(async () => {
    if (stockFlash.isOutOfStock || isAdding) return;

    setIsAdding(true);
    try {
      onAddToCart?.(product);
    } finally {
      setTimeout(() => setIsAdding(false), 400);
    }
  }, [stockFlash.isOutOfStock, isAdding, onAddToCart, product]);

  return (
    <div
      className={`group relative overflow-hidden rounded-xl border bg-white shadow-sm transition-all duration-300 hover:shadow-lg ${flashClasses} ${
        stockFlash.isCritical && !stockFlash.isOutOfStock
          ? 'border-red-200 hover:border-red-300'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      {/* Product Image */}
      <ProductImage
        src={product.image_url}
        alt={product.name}
        isCritical={stockFlash.isCritical}
        isOutOfStock={stockFlash.isOutOfStock}
        isFlashing={stockFlash.isFlashing}
      />

      {/* Product Info */}
      <div className="p-4">
        {/* Category Tag */}
        <div className="mb-2">
          <span className="inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
            {product.category.name}
          </span>
        </div>

        {/* Product Name */}
        <h3 className="mb-2 line-clamp-2 min-h-[2.75rem] text-base font-semibold leading-tight text-slate-800">
          {product.name}
        </h3>

        {/* Price Section */}
        <div className="mb-3 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-primary">
            {formatPrice(product.price)}
          </span>
        </div>

        {/* Stock Progress Bar */}
        <div className="mb-3">
          <StockProgressBar
            percentage={stockFlash.percentage}
            isFlashing={stockFlash.isFlashing}
            isCritical={stockFlash.isCritical}
            isOutOfStock={stockFlash.isOutOfStock}
          />
          {stockFlash.isCritical && !stockFlash.isOutOfStock && (
            <p className="mt-1 text-xs font-medium text-red-500">
              庫存緊張！手慢無
            </p>
          )}
        </div>

        {/* Stock Badge & Add to Cart */}
        <div className="flex items-center justify-between gap-3">
          <StockBadge
            stock={stockFlash.stock}
            isFlashing={stockFlash.isFlashing}
            changeAmount={stockFlash.changeAmount}
            changeDirection={stockFlash.changeDirection}
            isCritical={stockFlash.isCritical}
            isOutOfStock={stockFlash.isOutOfStock}
          />

          <button
            onClick={handleAddToCart}
            disabled={stockFlash.isOutOfStock || isAdding}
            className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${
              stockFlash.isOutOfStock
                ? 'cursor-not-allowed bg-slate-100 text-slate-400'
                : isAdding
                  ? 'bg-primary/80 text-white'
                  : stockFlash.isCritical
                    ? 'bg-gradient-to-r from-red-500 to-orange-500 text-white shadow-md hover:shadow-lg hover:brightness-110'
                    : 'bg-primary text-white hover:bg-primary/90'
            }`}
          >
            {isAdding ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
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
              </>
            ) : stockFlash.isOutOfStock ? (
              '已售罄'
            ) : stockFlash.isCritical ? (
              <>
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" />
                </svg>
                搶購
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
                加入
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export const ProductCardEnhanced = memo(ProductCardEnhancedComponent);
