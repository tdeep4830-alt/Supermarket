/**
 * ProductCard Skeleton Component.
 *
 * Ref: .blueprint/frontend_structure.md §3A
 * Shows loading placeholder to prevent layout shift (CLS).
 */

import { memo } from 'react';

function ProductCardSkeletonComponent() {
  return (
    <div className="overflow-hidden rounded-lg border bg-card shadow-sm">
      {/* Image skeleton */}
      <div className="aspect-square animate-pulse bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200" />

      {/* Content skeleton */}
      <div className="p-4">
        {/* Category */}
        <div className="mb-2 h-3 w-16 animate-pulse rounded bg-gray-200" />

        {/* Name */}
        <div className="mb-1 h-5 w-full animate-pulse rounded bg-gray-200" />
        <div className="mb-3 h-5 w-3/4 animate-pulse rounded bg-gray-200" />

        {/* Price */}
        <div className="mb-3 h-7 w-24 animate-pulse rounded bg-gray-200" />

        {/* Progress bar */}
        <div className="mb-3 h-2 w-full animate-pulse rounded-full bg-gray-200" />

        {/* Bottom row */}
        <div className="flex items-center justify-between">
          <div className="h-7 w-16 animate-pulse rounded-full bg-gray-200" />
          <div className="h-9 w-28 animate-pulse rounded-md bg-gray-200" />
        </div>
      </div>
    </div>
  );
}

export const ProductCardSkeleton = memo(ProductCardSkeletonComponent);
