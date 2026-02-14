/**
 * Admin Inventory Table Component.
 *
 * Features:
 * - Displays inventory with real-time stock updates
 * - Uses useStockFlash hook for stock change animations
 * - Restock button for each product
 */

import { useState } from 'react';
import { useAdminInventory } from '../hooks/useAdminInventory';
import { useStockFlash, /* getStockBadgeColor, */ getProgressBarColor } from '../../products/hooks/useStockFlash';
import { RestockModal } from './RestockModal';
import { ProductFormModal } from './ProductFormModal';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../api/client';
import { useAddToast } from '../../../store/toastStore';
import type { InventoryItem } from '../types';
import { formatPrice } from '../../../utils/format';

interface InventoryTableProps {
  searchTerm?: string;
  statusFilter?: string;
}

export function InventoryTable({ searchTerm, statusFilter }: InventoryTableProps): JSX.Element {
  const { data: inventory, isLoading, isError, refetch } = useAdminInventory(searchTerm, statusFilter);
  const [selectedProduct, setSelectedProduct] = useState<InventoryItem | null>(null);
  const [showRestockModal, setShowRestockModal] = useState(false);
  const [showProductFormModal, setShowProductFormModal] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [initialFormData, setInitialFormData] = useState<Record<string, unknown>>({});
  const [productFormProductId, setProductFormProductId] = useState<string>("");
  const addToast = useAddToast();

  const handleRestock = (product: InventoryItem) => {
    setSelectedProduct(product);
    setShowRestockModal(true);
  };

  const handleRestockSuccess = () => {
    // Refresh inventory list after successful restock
    refetch();
    setSelectedProduct(null);
    setShowRestockModal(false);
  };

  const handleEdit = (product: InventoryItem) => {
    setFormMode('edit');
    setInitialFormData({
      name: product.name,
      price: Number(product.price),
      categoryId: product.category.id,
      description: '',
      imageUrl: '',
    });
    setProductFormProductId(product.id);
    setSelectedProduct(product);
    setShowProductFormModal(true);
  };

  const handleDelete = async (product: InventoryItem) => {
    if (!window.confirm(`Are you sure you want to delete "${product.name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await apiClient.delete(`/admin/products/${product.id}/`);
      if (response.data.success) {
        addToast({ type: 'success', message: `Product "${product.name}" deleted successfully` });
        refetch();
      } else {
        addToast({ type: 'error', message: 'Failed to delete product' });
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: { message?: string } } } };
      const errorMessage = err.response?.data?.error?.message || 'Failed to delete product';
      addToast({ type: 'error', message: errorMessage });
      console.error('Product deletion failed:', error);
    }
  };

  // Fetch categories for the form
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await apiClient.get('/products/categories/');
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading inventory...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-red-700">Failed to load inventory. Please try again.</p>
          </div>
        </div>
      </div>
    );
  }

  if (!inventory || inventory.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No inventory items found.</p>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Product
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stock
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {inventory.map((item) => (
                <InventoryRow
                  key={item.id}
                  item={item}
                  onRestock={() => handleRestock(item)}
                  onEdit={() => handleEdit(item)}
                  onDelete={() => handleDelete(item)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showRestockModal && selectedProduct && (
        <RestockModal
          product={selectedProduct}
          onClose={() => {
            setShowRestockModal(false);
            setSelectedProduct(null);
          }}
          onSuccess={handleRestockSuccess}
        />
      )}

      {showProductFormModal && (
        <ProductFormModal
          isOpen={showProductFormModal}
          onClose={() => {
            setShowProductFormModal(false);
            setSelectedProduct(null);
            setInitialFormData({});
          }}
          mode={formMode}
          productId={productFormProductId}
          initialData={initialFormData}
          categoryOptions={categories}
        />
      )}
    </>
  );
}

interface InventoryRowProps {
  item: InventoryItem;
  onRestock: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

function InventoryRow({ item, onRestock, onEdit, onDelete }: InventoryRowProps): JSX.Element {
  // Use useStockFlash hook to get real-time stock animation
  const stockFlash = useStockFlash(item.stock, {
    maxStock: 100,
    flashDuration: 1000,
    criticalThreshold: 10,
  });

  // const badgeColor = getStockBadgeColor(stockFlash);
  const progressColor = getProgressBarColor(stockFlash);

  const getStatusDisplay = () => {
    switch (item.status) {
      case 'out_of_stock':
        return { text: 'Out of Stock', color: 'text-red-600', bgColor: 'bg-red-50' };
      case 'low_stock':
        return { text: 'Low Stock', color: 'text-orange-600', bgColor: 'bg-orange-50' };
      default:
        return { text: 'In Stock', color: 'text-green-600', bgColor: 'bg-green-50' };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900">{item.name}</div>
            <div className="text-xs text-gray-500 mt-1">ID: {item.id.slice(0, 8)}...</div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm text-gray-900">{item.category.name}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className={`text-sm font-medium ${stockFlash.isOutOfStock ? 'text-gray-500' : ''}`}>
          <span className={stockFlash.isFlashing ? 'animate-pulse' : ''}>
            {stockFlash.stock}
          </span>
          {stockFlash.isFlashing && stockFlash.changeDirection && (
            <span
              className={`ml-2 text-xs animate-pulse ${
                stockFlash.changeDirection === 'down' ? 'text-red-600' : 'text-green-600'
              }`}
            >
              {stockFlash.changeDirection === 'down' ? '-' : '+'}{stockFlash.changeAmount}
            </span>
          )}
        </div>
        <div className={`mt-1 w-16 h-1 rounded ${progressColor} transition-all`}
          style={{ width: `${stockFlash.percentage}%` }}
        />
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm text-gray-900">{formatPrice(item.price)}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusDisplay.bgColor} ${statusDisplay.color}`}>
          {statusDisplay.text}
        </span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right">
        <div className="flex justify-end space-x-2">
          <button
            onClick={onEdit}
            className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            title="Edit Product"
          >
            Edit
          </button>
          <button
            onClick={onRestock}
            className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Restock
          </button>
          <button
            onClick={onDelete}
            className="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}
