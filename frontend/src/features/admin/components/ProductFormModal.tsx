/**
 * Product Form Modal Component.
 *
 * Handles both create and update product operations with React Hook Form + Zod validation.
 * Supports real-time updates and error handling.
 *
 * Ref: .blueprint/code_structure.md §2 - Frontend Form Validation
 */

import { useEffect } from 'react';
import { useForm, type SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  XMarkIcon,
  PlusIcon,
  PencilSquareIcon,
  PhotoIcon,
} from '@heroicons/react/24/outline';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../../../api/client';
import { useAddToast } from '../../../store/toastStore';

// Form validation schema
const productSchema = z.object({
  name: z
    .string()
    .min(1, 'Product name is required')
    .max(200, 'Name must be 200 characters or less'),
  price: z.number().min(0.01, 'Price must be greater than 0'),
  categoryId: z.string().uuid('Invalid category ID'),
  description: z.string().max(500, 'Description must be 500 characters or less').optional(),
  imageUrl: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  initialStock: z.number().min(0, 'Stock cannot be negative'),
});

type ProductFormData = z.infer<typeof productSchema>;

interface ProductFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode: 'create' | 'edit';
  productId?: string;
  initialData?: Partial<ProductFormData>;
  categoryOptions: { id: string; name: string }[];
}

export function ProductFormModal({
  isOpen,
  onClose,
  mode,
  productId,
  initialData,
  categoryOptions,
}: ProductFormModalProps): JSX.Element {
  const queryClient = useQueryClient();
  const addToast = useAddToast();

  // Initialize form
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormData>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      name: '',
      price: 0,
      categoryId: '',
      description: '',
      imageUrl: '',
      initialStock: 0,
      ...(initialData || {}),
    },
  });

  // Reset form when modal opens/closes or mode changes
  useEffect(() => {
    if (isOpen) {
      reset({
        name: '',
        price: 0,
        categoryId: '',
        description: '',
        imageUrl: '',
        initialStock: 0,
        ...initialData,
      });
    }
  }, [isOpen, initialData, reset]);

  // Create product mutation
  const createMutation = useMutation({
    mutationFn: async (data: ProductFormData) => {
      const response = await apiClient.post('/admin/products/', {
        name: data.name,
        price: data.price,
        category_id: data.categoryId,
        description: data.description,
        image_url: data.imageUrl,
        initial_stock: data.initialStock,
      });
      return response.data;
    },
    onSuccess: () => {
      addToast({ type: 'success', message: 'Product created successfully' });
      queryClient.invalidateQueries({ queryKey: ['admin-inventory'] });
      onClose();
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { error?: { message?: string }; message?: string } } };
      const errorMessage =
        err.response?.data?.error?.message ||
        err.response?.data?.message ||
        'Failed to create product';
      addToast({ type: 'error', message: errorMessage });
      console.error('Product creation failed:', error);
    },
  });

  // Update product mutation
  const updateMutation = useMutation({
    mutationFn: async (data: ProductFormData) => {
      // Remove initialStock from update payload - only used for creation
      const { initialStock: _, ...updateData } = data;
      void _;
      const response = await apiClient.patch(
        `/admin/products/${productId}/`,
        updateData
      );
      return response.data;
    },
    onSuccess: () => {
      addToast({ type: 'success', message: 'Product updated successfully' });
      queryClient.invalidateQueries({ queryKey: ['admin-inventory'] });
      onClose();
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { error?: { message?: string }; message?: string } } };
      const errorMessage =
        err.response?.data?.error?.message ||
        err.response?.data?.message ||
        'Failed to update product';
      addToast({ type: 'error', message: errorMessage });
      console.error('Product update failed:', error);
    },
  });

  // Submit handler
  const onSubmit: SubmitHandler<ProductFormData> = (data) => {
    if (mode === 'create') {
      createMutation.mutate(data);
    } else {
      updateMutation.mutate(data);
    }
  };

  if (!isOpen) return null;

  const isLoading = isSubmitting || createMutation.isPending || updateMutation.isPending;

  return (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity z-[9998]"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div className="relative z-[9999] flex items-center justify-center min-h-screen p-4">
        {/* Modal */}
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-screen overflow-y-auto">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {mode === 'create' ? (
                  <>
                    <PlusIcon className="inline-block h-5 w-5 mr-2 text-blue-600" />
                    Add New Product
                  </>
                ) : (
                  <>
                    <PencilSquareIcon className="inline-block h-5 w-5 mr-2 text-green-600" />
                    Edit Product
                  </>
                )}
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-500 focus:outline-none"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="px-6 py-4">
            <div className="space-y-6">
              {/* Product Name */}
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                  Product Name *
                </label>
                <input
                  id="name"
                  type="text"
                  {...register('name')}
                  className={`block w-full rounded-md border ${
                    errors.name ? 'border-red-300' : 'border-gray-300'
                  } px-3 py-2 text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
                  placeholder="Enter product name"
                  disabled={isLoading}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              {/* Price */}
              <div>
                <label htmlFor="price" className="block text-sm font-medium text-gray-700 mb-2">
                  Price ($) *
                </label>
                <input
                  id="price"
                  type="number"
                  step="0.01"
                  min="0.01"
                  {...register('price', { valueAsNumber: true })}
                  className={`block w-full rounded-md border ${
                    errors.price ? 'border-red-300' : 'border-gray-300'
                  } px-3 py-2 text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
                  placeholder="0.00"
                  disabled={isLoading}
                />
                {errors.price && (
                  <p className="mt-1 text-sm text-red-600">{errors.price.message}</p>
                )}
              </div>

              {/* Category */}
              <div>
                <label htmlFor="categoryId" className="block text-sm font-medium text-gray-700 mb-2">
                  Category *
                </label>
                <select
                  id="categoryId"
                  {...register('categoryId')}
                  className={`block w-full rounded-md border ${
                    errors.categoryId ? 'border-red-300' : 'border-gray-300'
                  } px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
                  disabled={isLoading}
                >
                  <option value="">Select a category</option>
                  {categoryOptions.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </select>
                {errors.categoryId && (
                  <p className="mt-1 text-sm text-red-600">{errors.categoryId.message}</p>
                )}
              </div>

              {/* Description */}
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  id="description"
                  {...register('description')}
                  rows={3}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Product description (optional)"
                  disabled={isLoading}
                />
                {errors.description && (
                  <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
                )}
              </div>

              {/* Image URL */}
              <div>
                <label htmlFor="imageUrl" className="block text-sm font-medium text-gray-700 mb-2">
                  Image URL
                </label>
                <div className="relative">
                  <input
                    id="imageUrl"
                    type="url"
                    {...register('imageUrl')}
                    className={`block w-full rounded-md border ${
                      errors.imageUrl ? 'border-red-300' : 'border-gray-300'
                    } pl-3 pr-10 py-2 text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
                    placeholder="https://example.com/image.jpg"
                    disabled={isLoading}
                  />
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                    <PhotoIcon className="h-4 w-4 text-gray-400" />
                  </div>
                </div>
                {errors.imageUrl && (
                  <p className="mt-1 text-sm text-red-600">{errors.imageUrl.message}</p>
                )}
              </div>

              {/* Initial Stock (Only for Create Mode) */}
              {mode === 'create' && (
                <div>
                  <label
                    htmlFor="initialStock"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Initial Stock
                  </label>
                  <input
                    id="initialStock"
                    type="number"
                    min="0"
                    {...register('initialStock', { valueAsNumber: true })}
                    className={`block w-full rounded-md border ${
                      errors.initialStock ? 'border-red-300' : 'border-gray-300'
                    } px-3 py-2 text-sm shadow-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500`}
                    placeholder="0"
                    disabled={isLoading}
                  />
                  {errors.initialStock && (
                    <p className="mt-1 text-sm text-red-600">{errors.initialStock.message}</p>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="mt-6 flex justify-end space-x-3 border-t border-gray-200 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                disabled={isLoading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
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
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Processing...
                  </>
                ) : mode === 'create' ? (
                  <>
                    <PlusIcon className="-ml-1 mr-2 h-4 w-4" />
                    Create Product
                  </>
                ) : (
                  <>
                    <PencilSquareIcon className="-ml-1 mr-2 h-4 w-4" />
                    Update Product
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
