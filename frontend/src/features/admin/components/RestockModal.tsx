/**
 * Restock Modal Component.
 *
 * Allows admins to add stock to products.
 */

import { useState } from 'react';
import { useRestockProduct } from '../hooks/useAdminInventory';
import { InventoryItem } from '../types';

interface RestockModalProps {
  product: InventoryItem;
  onClose: () => void;
  onSuccess: () => void;
}

export function RestockModal({ product, onClose, onSuccess }: RestockModalProps): JSX.Element {
  const [quantity, setQuantity] = useState<number>(10);
  const { mutate: restockProduct, isPending } = useRestockProduct();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (quantity <= 0) {
      return;
    }

    restockProduct(
      { productId: product.id, quantity },
      {
        onSuccess: () => {
          onSuccess();
        },
      }
    );
  };

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto"
      onClick={handleOverlayClick}
      aria-labelledby="restock-modal-title"
      role="dialog"
      aria-modal="true"
    >
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />

        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">
          &#8203;
        </span>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                <h3 className="text-lg leading-6 font-medium text-gray-900" id="restock-modal-title">
                  Restock Product
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-gray-500">
                    Add stock to <span className="font-medium">{product.name}</span>
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="mt-4">
                  <div className="bg-gray-50 rounded-md p-4 mb-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Current Stock:</span>
                        <p className="font-medium">{product.stock} units</p>
                      </div>
                      <div>
                        <span className="text-gray-500">Category:</span>
                        <p className="font-medium">{product.category.name}</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="quantity" className="block text-sm font-medium text-gray-700">
                      Quantity to Add
                    </label>
                    <div className="mt-1">
                      <input
                        type="number"
                        id="quantity"
                        min="1"
                        max="9999"
                        value={quantity}
                        onChange={(e) => setQuantity(parseInt(e.target.value || '0', 10))}
                        className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md px-3 py-2"
                        placeholder="Enter quantity"
                        required
                        disabled={isPending}
                      />
                    </div>
                    <p className="mt-2 text-sm text-gray-500">
                      Enter the number of units to add to the current stock.
                    </p>
                  </div>
                </form>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isPending || quantity <= 0}
              className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Restocking...
                </>
              ) : (
                'Restock'
              )}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
