/**
 * Admin Portal Feature Entry Point.
 */

// Components
export { AdminRoute } from './components/AdminRoute';
export { AdminLayout } from './components/AdminLayout';
export { InventoryTable } from './components/InventoryTable';
export { RestockModal } from './components/RestockModal';

// Pages
export { InventoryPage } from './pages/InventoryPage';

// Hooks
export { useAdminInventory, useRestockProduct } from './hooks/useAdminInventory';

// Types
export type {
  InventoryItem,
  RestockResponse,
  RestockVariables,
  OrderItem,
  AdminOrdersResponse,
  PaginationMetadata,
} from './types';
