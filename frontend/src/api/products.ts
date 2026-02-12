/**
 * Products API Functions.
 *
 * Ref: Backend - apps/products/views.py (to be implemented)
 */

import type { Product, ProductWithStock, UUID } from '@/types';
import apiClient from './client';

// =============================================================================
// Mock Data (for development before backend is ready)
// =============================================================================

const USE_MOCK = true; // Set to false when backend is ready

const mockProducts: ProductWithStock[] = [
  {
    id: '1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p',
    name: '有機蘋果 (6入)',
    description: '新鮮直送的有機蘋果，產地直銷',
    price: '199.00',
    image_url: 'https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=300&h=300&fit=crop',
    is_active: true,
    category: { id: 'cat-1', name: '新鮮水果', slug: 'fresh-fruits' },
    created_at: new Date().toISOString(),
    stock: 5, // Low stock
  },
  {
    id: '2b3c4d5e-6f7g-8h9i-0j1k-2l3m4n5o6p7q',
    name: '特級和牛 A5 (200g)',
    description: '日本進口頂級和牛，入口即化',
    price: '1280.00',
    image_url: 'https://images.unsplash.com/photo-1546964124-0cce460f38ef?w=300&h=300&fit=crop',
    is_active: true,
    category: { id: 'cat-2', name: '肉類海鮮', slug: 'meat-seafood' },
    created_at: new Date().toISOString(),
    stock: 3, // Very low stock
  },
  {
    id: '3c4d5e6f-7g8h-9i0j-1k2l-3m4n5o6p7q8r',
    name: '北海道牛奶 (1L)',
    description: '100% 北海道產鮮乳',
    price: '89.00',
    image_url: 'https://images.unsplash.com/photo-1563636619-e9143da7973b?w=300&h=300&fit=crop',
    is_active: true,
    category: { id: 'cat-3', name: '乳製品', slug: 'dairy' },
    created_at: new Date().toISOString(),
    stock: 50,
  },
  {
    id: '4d5e6f7g-8h9i-0j1k-2l3m-4n5o6p7q8r9s',
    name: '有機雞蛋 (10入)',
    description: '放養雞所產的有機雞蛋',
    price: '120.00',
    image_url: 'https://images.unsplash.com/photo-1518569656558-1f25e69d93d7?w=300&h=300&fit=crop',
    is_active: true,
    category: { id: 'cat-3', name: '乳製品', slug: 'dairy' },
    created_at: new Date().toISOString(),
    stock: 0, // Out of stock
  },
  {
    id: '5e6f7g8h-9i0j-1k2l-3m4n-5o6p7q8r9s0t',
    name: '法式長棍麵包',
    description: '每日新鮮現烤',
    price: '45.00',
    image_url: 'https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=300&h=300&fit=crop',
    is_active: true,
    category: { id: 'cat-4', name: '烘焙麵包', slug: 'bakery' },
    created_at: new Date().toISOString(),
    stock: 25,
  },
  {
    id: '6f7g8h9i-0j1k-2l3m-4n5o-6p7q8r9s0t1u',
    name: '有機菠菜 (300g)',
    description: '無農藥栽培',
    price: '65.00',
    image_url: 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=300&h=300&fit=crop',
    is_active: true,
    category: { id: 'cat-5', name: '新鮮蔬菜', slug: 'vegetables' },
    created_at: new Date().toISOString(),
    stock: 8, // Low stock
  },
  {
    id: '7g8h9i0j-1k2l-3m4n-5o6p-7q8r9s0t1u2v',
    name: '挪威鮭魚 (300g)',
    description: '冷鏈空運直送',
    price: '350.00',
    image_url: 'https://images.unsplash.com/photo-1599084993091-1cb5c0721cc6?w=300&h=300&fit=crop',
    is_active: true,
    category: { id: 'cat-2', name: '肉類海鮮', slug: 'meat-seafood' },
    created_at: new Date().toISOString(),
    stock: 15,
  },
  {
    id: '8h9i0j1k-2l3m-4n5o-6p7q-8r9s0t1u2v3w',
    name: '進口藍莓 (125g)',
    description: '智利空運新鮮藍莓',
    price: '159.00',
    image_url: 'https://images.unsplash.com/photo-1498557850523-fd3d118b962e?w=300&h=300&fit=crop',
    is_active: true,
    category: { id: 'cat-1', name: '新鮮水果', slug: 'fresh-fruits' },
    created_at: new Date().toISOString(),
    stock: 2, // Very low stock - flash sale item
  },
];

// Simulate stock changes for demo
function getRandomizedStock(): ProductWithStock[] {
  return mockProducts.map((product) => ({
    ...product,
    // Randomly decrease stock to simulate real-time changes
    stock: Math.max(0, product.stock - Math.floor(Math.random() * 2)),
  }));
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get all active products.
 */
export async function getProducts(): Promise<ProductWithStock[]> {
  if (USE_MOCK) {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 500));
    return getRandomizedStock();
  }

  const response = await apiClient.get<{ products: Product[] }>('/products/');
  return response.data.products as ProductWithStock[];
}

/**
 * Get product with stock info by ID.
 */
export async function getProductById(
  productId: UUID
): Promise<ProductWithStock> {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 300));
    const product = mockProducts.find((p) => p.id === productId);
    if (!product) throw new Error('Product not found');
    return product;
  }

  const response = await apiClient.get<ProductWithStock>(
    `/products/${productId}/`
  );
  return response.data;
}

/**
 * Get products by category.
 */
export async function getProductsByCategory(
  categorySlug: string
): Promise<ProductWithStock[]> {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 400));
    return mockProducts.filter((p) => p.category.slug === categorySlug);
  }

  const response = await apiClient.get<{ products: Product[] }>(
    `/products/category/${categorySlug}/`
  );
  return response.data.products as ProductWithStock[];
}
