/**
 * Product & Category TypeScript Interfaces.
 *
 * Ref: .blueprint/data.md §1A, §1B
 * Ref: Backend serializers - apps/products/serializers.py
 */

import type { DecimalString, ISODateTime, UUID } from './common';

// =============================================================================
// Category Types
// =============================================================================

export interface Category {
  id: UUID;
  name: string;
  slug: string;
  parent: UUID | null;
  is_active: boolean;
}

export interface CategoryNested {
  id: UUID;
  name: string;
  slug: string;
}

// =============================================================================
// Product Types
// =============================================================================

export interface Product {
  id: UUID;
  name: string;
  description: string;
  price: DecimalString;
  image_url: string;
  is_active: boolean;
  category: CategoryNested;
  created_at: ISODateTime;
}

export interface ProductWithStock extends Product {
  stock: number;
}

export interface ProductMinimal {
  id: UUID;
  name: string;
  price: DecimalString;
  image_url: string;
}

// =============================================================================
// Stock Helpers
// =============================================================================

export interface StockStatus {
  quantity: number;
  isLow: boolean;
  isOutOfStock: boolean;
  percentage: number;
}

export function calculateStockStatus(
  current: number,
  original: number = 100
): StockStatus {
  const percentage = original > 0 ? (current / original) * 100 : 0;
  return {
    quantity: current,
    isLow: percentage < 10 && current > 0,
    isOutOfStock: current === 0,
    percentage,
  };
}
