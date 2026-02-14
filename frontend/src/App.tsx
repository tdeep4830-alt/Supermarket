/**
 * Main App Component.
 *
 * Ref: .blueprint/frontend_structure.md
 * Ref: .blueprint/auth.md §7 - Frontend Integration
 */

import { useState, useCallback, useEffect } from 'react';
import { User, LogOut, LogIn, UserPlus, ShoppingBag, LayoutDashboard, Truck } from 'lucide-react';
import { ProductsPage } from '@/features/products';
import { CartButton, CartDrawer } from '@/features/cart';
import { CheckoutPage, OrderSuccessPage } from '@/features/checkout';
import { LoginPage, RegisterPage, ProtectedRoute } from '@/features/auth';
import { AdminRoute, InventoryPage } from '@/features/admin';
import { DeliverySlotsPage } from '@/features/admin/pages/DeliverySlotsPage';
import { ToastContainer } from '@/components/Toast';
import { useAuthStore, useUser, useIsAuthenticated, useAddToast } from '@/store';
import type { PlaceOrderResponse } from '@/types';

type AppView = 'products' | 'checkout' | 'order-success' | 'login' | 'register' | 'admin-inventory' | 'admin-delivery-slots';

function App() {
  const [currentView, setCurrentView] = useState<AppView>('products');
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [lastOrder, setLastOrder] = useState<PlaceOrderResponse | null>(null);
  const [pendingCheckout, setPendingCheckout] = useState(false);

  // Auth state
  const user = useUser();
  const isAuthenticated = useIsAuthenticated();
  const { checkAuth, logout, isLoading: authLoading } = useAuthStore();
  const addToast = useAddToast();

  // Initialize auth on app load (Ref: auth.md §7)
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const handleOpenCart = useCallback(() => setIsCartOpen(true), []);
  const handleCloseCart = useCallback(() => setIsCartOpen(false), []);

  const handleCheckout = useCallback(() => {
    setIsCartOpen(false);
    if (!isAuthenticated) {
      setPendingCheckout(true);
      setCurrentView('login');
      addToast({
        type: 'info',
        message: 'Please sign in to checkout',
      });
    } else {
      setCurrentView('checkout');
    }
  }, [isAuthenticated, addToast]);

  const handleBackToProducts = useCallback(() => {
    setCurrentView('products');
    setPendingCheckout(false);
  }, []);

  const handleOrderComplete = useCallback((order: PlaceOrderResponse) => {
    setLastOrder(order);
    setCurrentView('order-success');
  }, []);

  const handleLogoClick = useCallback(() => {
    setCurrentView('products');
    setLastOrder(null);
    setPendingCheckout(false);
  }, []);

  // Auth navigation handlers
  const handleLoginClick = useCallback(() => {
    setCurrentView('login');
  }, []);

  const handleRegisterClick = useCallback(() => {
    setCurrentView('register');
  }, []);

  const handleAuthSuccess = useCallback(() => {
    if (pendingCheckout) {
      setPendingCheckout(false);
      setCurrentView('checkout');
      addToast({
        type: 'success',
        message: 'Welcome! You can now proceed to checkout.',
      });
    } else {
      setCurrentView('products');
      addToast({
        type: 'success',
        message: `Welcome${user ? `, ${user.username}` : ''}!`,
      });
    }
  }, [pendingCheckout, user, addToast]);

  const handleLogout = useCallback(async () => {
    await logout();
    setCurrentView('products');
    setPendingCheckout(false);
    addToast({
      type: 'info',
      message: 'You have been signed out.',
    });
  }, [logout, addToast]);

  const handleUnauthenticated = useCallback(() => {
    setPendingCheckout(true);
    setCurrentView('login');
  }, []);

  // Admin navigation
  const handleAdminClick = useCallback(() => {
    setCurrentView('admin-inventory');
  }, []);

  const handleDeliverySlotsClick = useCallback(() => {
    setCurrentView('admin-delivery-slots');
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={handleLogoClick}
              className="flex items-center gap-2 text-2xl font-bold text-primary hover:opacity-80"
            >
              <ShoppingBag className="h-7 w-7" />
              <span className="hidden sm:inline">Online Supermarket</span>
            </button>
            <nav className="flex items-center gap-3">
              {/* Auth Navigation */}
              {isAuthenticated ? (
                <div className="flex items-center gap-3">
                  {/* User Info */}
                  <div className="flex items-center gap-2 rounded-lg bg-accent px-3 py-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-foreground">
                      {user?.username}
                    </span>
                  </div>
                  {/* Admin Button (for staff users) */}
                  {user?.is_staff && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleAdminClick}
                        className={`flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-foreground ${
                          currentView === 'admin-inventory' ? 'bg-accent text-foreground' : 'text-muted-foreground'
                        }`}
                      >
                        <LayoutDashboard className="h-4 w-4" />
                        <span className="hidden sm:inline">庫存</span>
                      </button>
                      <button
                        onClick={handleDeliverySlotsClick}
                        className={`flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-foreground ${
                          currentView === 'admin-delivery-slots' ? 'bg-accent text-foreground' : 'text-muted-foreground'
                        }`}
                      >
                        <Truck className="h-4 w-4" />
                        <span className="hidden sm:inline">配送</span>
                      </button>
                    </div>
                  )}
                  {/* Logout Button */}
                  <button
                    onClick={handleLogout}
                    disabled={authLoading}
                    className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
                  >
                    <LogOut className="h-4 w-4" />
                    <span className="hidden sm:inline">Sign Out</span>
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  {/* Login Button */}
                  <button
                    onClick={handleLoginClick}
                    className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  >
                    <LogIn className="h-4 w-4" />
                    <span className="hidden sm:inline">Sign In</span>
                  </button>
                  {/* Register Button */}
                  <button
                    onClick={handleRegisterClick}
                    className="flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                  >
                    <UserPlus className="h-4 w-4" />
                    <span className="hidden sm:inline">Sign Up</span>
                  </button>
                </div>
              )}
              {/* Cart Button */}
              <CartButton onClick={handleOpenCart} />
            </nav>
          </div>
        </div>
      </header>

      {/* Flash Sale Banner */}
      {currentView === 'products' && (
        <div className="bg-gradient-to-r from-red-500 to-orange-500 py-2 text-center text-sm font-medium text-white">
          Limited Time Flash Sale! Real-time stock updates - act fast!
        </div>
      )}

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {currentView === 'products' && <ProductsPage />}

        {currentView === 'login' && (
          <LoginPage
            onSuccess={handleAuthSuccess}
            onRegisterClick={handleRegisterClick}
          />
        )}

        {currentView === 'register' && (
          <RegisterPage
            onSuccess={handleAuthSuccess}
            onLoginClick={handleLoginClick}
          />
        )}

        {currentView === 'checkout' && (
          <ProtectedRoute onUnauthenticated={handleUnauthenticated}>
            <CheckoutPage
              onBack={handleBackToProducts}
              onOrderComplete={handleOrderComplete}
            />
          </ProtectedRoute>
        )}

        {currentView === 'order-success' && lastOrder && (
          <OrderSuccessPage
            orderResponse={lastOrder}
            onContinueShopping={handleBackToProducts}
          />
        )}

        {currentView === 'admin-inventory' && (
          <AdminRoute>
            <InventoryPage />
          </AdminRoute>
        )}

        {currentView === 'admin-delivery-slots' && (
          <AdminRoute>
            <DeliverySlotsPage />
          </AdminRoute>
        )}
      </main>

      {/* Cart Drawer */}
      <CartDrawer
        isOpen={isCartOpen}
        onClose={handleCloseCart}
        onCheckout={handleCheckout}
      />

      {/* Toast Notifications */}
      <ToastContainer />

      {/* Footer */}
      <footer className="mt-auto border-t border-border bg-card py-6">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>2024 Online Supermarket. Built with React + Django.</p>
          <p className="mt-1">
            React Query (Stock Sync) + Zustand + Tailwind CSS + TypeScript
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
