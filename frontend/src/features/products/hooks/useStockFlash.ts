/**
 * useStockFlash Hook.
 *
 * Ref: .blueprint/frontend_structure.md §4A
 *
 * Features:
 * - Real-time stock monitoring with visual flash effect
 * - Detects stock changes and triggers animation
 * - Uses React Query for automatic refetching
 */

import { useEffect, useRef, useState } from 'react';

export interface StockFlashState {
  /** Current stock value */
  stock: number;
  /** Previous stock value before update */
  previousStock: number | null;
  /** Whether stock is currently flashing (changed recently) */
  isFlashing: boolean;
  /** Direction of stock change */
  changeDirection: 'up' | 'down' | null;
  /** Amount of stock change */
  changeAmount: number;
  /** Whether stock is critically low (< 10) */
  isCritical: boolean;
  /** Whether item is out of stock */
  isOutOfStock: boolean;
  /** Stock percentage (based on max stock) */
  percentage: number;
}

interface UseStockFlashOptions {
  /** Maximum stock for percentage calculation */
  maxStock?: number;
  /** Duration of flash animation in ms */
  flashDuration?: number;
  /** Critical stock threshold */
  criticalThreshold?: number;
}

const DEFAULT_OPTIONS: Required<UseStockFlashOptions> = {
  maxStock: 100,
  flashDuration: 1000,
  criticalThreshold: 10,
};

/**
 * Hook for monitoring stock changes with visual flash effects.
 *
 * Usage:
 * ```tsx
 * function ProductCard({ product }) {
 *   const stockFlash = useStockFlash(product.stock);
 *
 *   return (
 *     <div className={stockFlash.isFlashing ? 'animate-pulse' : ''}>
 *       <span className={stockFlash.isCritical ? 'text-red-500' : ''}>
 *         Stock: {stockFlash.stock}
 *       </span>
 *       {stockFlash.isFlashing && stockFlash.changeDirection === 'down' && (
 *         <span className="text-red-500">-{stockFlash.changeAmount}</span>
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useStockFlash(
  currentStock: number,
  options?: UseStockFlashOptions
): StockFlashState {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const previousStockRef = useRef<number | null>(null);
  const flashTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [state, setState] = useState<StockFlashState>(() => ({
    stock: currentStock,
    previousStock: null,
    isFlashing: false,
    changeDirection: null,
    changeAmount: 0,
    isCritical: currentStock > 0 && currentStock <= opts.criticalThreshold,
    isOutOfStock: currentStock === 0,
    percentage: Math.min((currentStock / opts.maxStock) * 100, 100),
  }));

  // Handle stock changes
  useEffect(() => {
    const prevStock = previousStockRef.current;

    // Skip initial render
    if (prevStock === null) {
      previousStockRef.current = currentStock;
      return;
    }

    // Skip if stock hasn't changed
    if (prevStock === currentStock) {
      return;
    }

    // Calculate change
    const changeAmount = Math.abs(currentStock - prevStock);
    const changeDirection = currentStock > prevStock ? 'up' : 'down';

    // Clear existing timeout
    if (flashTimeoutRef.current) {
      clearTimeout(flashTimeoutRef.current);
    }

    // Update state with flash
    setState({
      stock: currentStock,
      previousStock: prevStock,
      isFlashing: true,
      changeDirection,
      changeAmount,
      isCritical: currentStock > 0 && currentStock <= opts.criticalThreshold,
      isOutOfStock: currentStock === 0,
      percentage: Math.min((currentStock / opts.maxStock) * 100, 100),
    });

    // Clear flash after duration
    flashTimeoutRef.current = setTimeout(() => {
      setState((prev) => ({
        ...prev,
        isFlashing: false,
        changeDirection: null,
        changeAmount: 0,
        previousStock: null,
      }));
    }, opts.flashDuration);

    // Update ref
    previousStockRef.current = currentStock;

    // Cleanup
    return () => {
      if (flashTimeoutRef.current) {
        clearTimeout(flashTimeoutRef.current);
      }
    };
  }, [currentStock, opts.criticalThreshold, opts.flashDuration, opts.maxStock]);

  return state;
}

/**
 * Get CSS classes for stock flash animation.
 */
export function getStockFlashClasses(state: StockFlashState): string {
  const classes: string[] = [];

  if (state.isFlashing) {
    classes.push('animate-pulse');
    if (state.changeDirection === 'down') {
      classes.push('ring-2 ring-red-400 ring-opacity-75');
    } else if (state.changeDirection === 'up') {
      classes.push('ring-2 ring-green-400 ring-opacity-75');
    }
  }

  if (state.isCritical) {
    classes.push('border-red-300');
  }

  if (state.isOutOfStock) {
    classes.push('opacity-60 grayscale');
  }

  return classes.join(' ');
}

/**
 * Get stock badge color based on state.
 */
export function getStockBadgeColor(state: StockFlashState): {
  bg: string;
  text: string;
  border: string;
} {
  if (state.isOutOfStock) {
    return { bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-200' };
  }
  if (state.isCritical) {
    return { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-200' };
  }
  if (state.percentage < 30) {
    return { bg: 'bg-orange-50', text: 'text-orange-600', border: 'border-orange-200' };
  }
  return { bg: 'bg-green-50', text: 'text-green-600', border: 'border-green-200' };
}

/**
 * Get progress bar color based on stock state.
 */
export function getProgressBarColor(state: StockFlashState): string {
  if (state.isOutOfStock) return 'bg-gray-300';
  if (state.isCritical) return 'bg-red-500';
  if (state.percentage < 30) return 'bg-orange-500';
  return 'bg-green-500';
}
