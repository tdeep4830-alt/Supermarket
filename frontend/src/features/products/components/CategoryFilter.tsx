/**
 * Category Filter Component.
 *
 * Ref: .blueprint/frontend_structure.md §2
 *
 * Features:
 * - Horizontal scrollable category tabs
 * - Active state styling
 * - "All" option
 * - Responsive design
 */

import { memo, useCallback, useRef, useEffect, useState } from 'react';
import type { Category } from '@/types';

interface CategoryFilterProps {
  categories: Category[];
  selectedCategory: string | null;
  onSelect: (categorySlug: string | null) => void;
  productCounts?: Record<string, number>;
}

function CategoryFilterComponent({
  categories,
  selectedCategory,
  onSelect,
  productCounts,
}: CategoryFilterProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showLeftShadow, setShowLeftShadow] = useState(false);
  const [showRightShadow, setShowRightShadow] = useState(false);

  // Check scroll position for shadow indicators
  const updateShadows = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;

    setShowLeftShadow(el.scrollLeft > 0);
    setShowRightShadow(el.scrollLeft < el.scrollWidth - el.clientWidth - 1);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    updateShadows();
    el.addEventListener('scroll', updateShadows);
    window.addEventListener('resize', updateShadows);

    return () => {
      el.removeEventListener('scroll', updateShadows);
      window.removeEventListener('resize', updateShadows);
    };
  }, [updateShadows]);

  const handleSelect = useCallback(
    (slug: string | null) => {
      onSelect(slug);
    },
    [onSelect]
  );

  // Get total product count
  const totalCount = productCounts
    ? Object.values(productCounts).reduce((sum, count) => sum + count, 0)
    : null;

  return (
    <div className="relative">
      {/* Left shadow indicator */}
      {showLeftShadow && (
        <div className="pointer-events-none absolute left-0 top-0 z-10 h-full w-8 bg-gradient-to-r from-background to-transparent" />
      )}

      {/* Right shadow indicator */}
      {showRightShadow && (
        <div className="pointer-events-none absolute right-0 top-0 z-10 h-full w-8 bg-gradient-to-l from-background to-transparent" />
      )}

      {/* Scrollable container */}
      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {/* All Categories Button */}
        <button
          onClick={() => handleSelect(null)}
          className={`flex-shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition-all ${
            selectedCategory === null
              ? 'border-primary bg-primary text-white shadow-md'
              : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
          }`}
        >
          <span className="flex items-center gap-2">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
              />
            </svg>
            全部商品
            {totalCount !== null && (
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  selectedCategory === null
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-100 text-slate-500'
                }`}
              >
                {totalCount}
              </span>
            )}
          </span>
        </button>

        {/* Category Buttons */}
        {categories.map((category) => {
          const count = productCounts?.[category.slug];
          const isSelected = selectedCategory === category.slug;

          return (
            <button
              key={category.id}
              onClick={() => handleSelect(category.slug)}
              className={`flex-shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition-all ${
                isSelected
                  ? 'border-primary bg-primary text-white shadow-md'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <span className="flex items-center gap-2">
                <CategoryIcon category={category.slug} />
                {category.name}
                {count !== undefined && (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      isSelected
                        ? 'bg-white/20 text-white'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {count}
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Category icon based on slug.
 */
function CategoryIcon({ category }: { category: string }) {
  const iconClass = 'h-4 w-4';

  switch (category) {
    case 'fresh-fruits':
      return <span className={iconClass}>🍎</span>;
    case 'vegetables':
      return <span className={iconClass}>🥬</span>;
    case 'meat-seafood':
      return <span className={iconClass}>🥩</span>;
    case 'dairy':
      return <span className={iconClass}>🥛</span>;
    case 'bakery':
      return <span className={iconClass}>🥖</span>;
    case 'beverages':
      return <span className={iconClass}>🧃</span>;
    case 'snacks':
      return <span className={iconClass}>🍿</span>;
    case 'frozen':
      return <span className={iconClass}>🧊</span>;
    default:
      return (
        <svg className={iconClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
          />
        </svg>
      );
  }
}

export const CategoryFilter = memo(CategoryFilterComponent);
