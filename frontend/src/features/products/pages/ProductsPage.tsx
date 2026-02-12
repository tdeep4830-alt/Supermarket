/**
 * Products Page Component.
 *
 * Ref: .blueprint/frontend_structure.md §4A
 * Main page showing product gallery with category filtering,
 * pagination, and real-time stock updates.
 */

import { ProductGallery } from './ProductGallery';

export function ProductsPage() {
  return <ProductGallery />;
}
