/**
 * Admin Inventory Management Page.
 *
 * Main page for managing product inventory with real-time stock updates.
 */

import { useState } from 'react';
import { MagnifyingGlassIcon, PlusIcon } from '@heroicons/react/24/outline';
import { AdminLayout } from '../components/AdminLayout';
import { InventoryTable as InventoryTableComponent } from '../components/InventoryTable';
import { ProductFormModal } from '../components/ProductFormModal';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../api/client';

export function InventoryPage(): JSX.Element {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showProductFormModal, setShowProductFormModal] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
  };

  const handleAddProduct = () => {
    setShowProductFormModal(true);
  };

  // Fetch categories for the form
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await apiClient.get('/admin/categories/');
      // Debug log
      console.log('Categories response:', response.data);
      // Ensure we return an array
      if (Array.isArray(response.data?.categories)) {
        return response.data.categories;
      }
      // Fallback to empty array
      return [];
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  return (
    <AdminLayout currentPage="inventory">
      <div className="space-y-6">
        {/* Header */}
        <div className="md:flex md:items-center md:justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
              Inventory Management
            </h2>
            <p className="mt-2 text-sm text-gray-700">
              Monitor and manage your product inventory with real-time stock updates.
            </p>
          </div>
          <div className="mt-4 md:mt-0">
            <button
              type="button"
              onClick={handleAddProduct}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              <PlusIcon className="-ml-1 mr-2 h-4 w-4" />
              Add Product
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1">
            <div className="flex rounded-md shadow-sm">
              <div className="relative flex items-stretch flex-grow focus-within:z-10">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full rounded-none rounded-l-md pl-10 sm:text-sm border-gray-300"
                  placeholder="Search products..."
                />
              </div>
              <button
                type="submit"
                className="-ml-px relative inline-flex items-center space-x-2 px-4 py-2 border border-gray-300 text-sm font-medium rounded-r-md text-gray-700 bg-gray-50 hover:bg-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              >
                Search
              </button>
            </div>
          </form>

          {/* Status Filter */}
          <div>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            >
              <option value="">All Status</option>
              <option value="in_stock">In Stock</option>
              <option value="low_stock">Low Stock</option>
              <option value="out_of_stock">Out of Stock</option>
            </select>
          </div>
        </div>

        {/* Legend */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3 flex-1">
              <div className="text-sm text-blue-700">
                <p>Stock levels update in real-time. Items with flashing numbers indicate recent changes.</p>
                <ul className="mt-2 list-disc list-inside space-y-1">
                  <li>Red: Out of stock</li>
                  <li>Orange: Low stock (≤ 10 units)</li>
                  <li>Green: In stock</li>
                  <li>Pulse animation: Stock change detected</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Debug: Show categories count */}
        {categories.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <p className="text-sm text-green-700">✓ 已載入 {categories.length} 個類別</p>
          </div>
        )}

        {/* Inventory Table */}
        <InventoryTableComponent searchTerm={searchTerm} statusFilter={statusFilter} />
      </div>

      {/* Add Product Modal */}
      {showProductFormModal && (
        <ProductFormModal
          isOpen={showProductFormModal}
          onClose={() => setShowProductFormModal(false)}
          mode="create"
          categoryOptions={categories}
          initialData={{}}
        />
      )}
    </AdminLayout>
  );
}
