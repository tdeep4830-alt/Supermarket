/**
 * Admin Layout Component.
 *
 * Provides dashboard layout with sidebar navigation for admin features.
 * Includes: Inventory Management, Order Management
 *
 * Note: This app uses state management instead of React Router
 */

import { useState } from 'react';
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline';

interface AdminLayoutProps {
  children: React.ReactNode;
  currentPage?: 'dashboard' | 'inventory' | 'delivery-slots' | 'orders';
  onNavigate?: (page: string) => void;
}

const navigation = [
  { name: 'Dashboard', page: 'dashboard', icon: '📊' },
  { name: 'Inventory Management', page: 'inventory', icon: '📦' },
  { name: 'Delivery Slots', page: 'delivery-slots', icon: '🚚' },
  { name: 'Order Management', page: 'orders', icon: '📋' },
];

export function AdminLayout({ children, currentPage = 'inventory', onNavigate }: AdminLayoutProps): JSX.Element {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleNavigation = (page: string) => {
    setSidebarOpen(false);
    if (onNavigate) {
      onNavigate(page);
    }
    // Default behavior: if inventory page, stay on inventory
    if (page === 'inventory' && !onNavigate) {
      // Already on inventory page
    }
  };

  const getPageTitle = () => {
    switch (currentPage) {
      case 'dashboard':
        return 'Dashboard';
      case 'inventory':
        return 'Inventory Management';
      case 'delivery-slots':
        return 'Delivery Slots';
      case 'orders':
        return 'Order Management';
      default:
        return 'Admin Portal';
    }
  };

  const isActive = (page: string) => {
    return page === currentPage;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex h-screen">
        {/* Sidebar for desktop */}
        <div className="hidden lg:flex lg:flex-shrink-0">
          <div className="flex flex-col w-64 border-r border-gray-200 bg-white">
            {/* Sidebar component */}
            <div className="flex-1 flex flex-col min-h-0">
              <div className="flex items-center justify-between h-16 flex-shrink-0 px-4 border-b border-gray-200">
                <button
                  onClick={() => handleNavigation('dashboard')}
                  className="flex items-center"
                >
                  <h1 className="text-xl font-semibold text-gray-900">Admin Portal</h1>
                </button>
              </div>
              <nav className="flex-1 px-2 py-4 bg-white">
                {navigation.map((item) => (
                  <button
                    key={item.name}
                    onClick={() => handleNavigation(item.page)}
                    className={`group flex items-center w-full text-left px-2 py-2 text-sm font-medium rounded-md ${
                      isActive(item.page)
                        ? 'bg-blue-50 text-blue-700 border-blue-200 border-l-4 pl-5'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 mx-1'
                    }`}
                  >
                    <span className="mr-3 text-lg">{item.icon}</span>
                    {item.name}
                  </button>
                ))}
              </nav>
            </div>
          </div>
        </div>

        {/* Mobile sidebar */}
        <div className={`lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-white ${sidebarOpen ? 'block' : 'hidden'}`}>
          <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
            <button
              onClick={() => handleNavigation('dashboard')}
              className="flex items-center"
            >
              <h1 className="text-xl font-semibold text-gray-900">Admin Portal</h1>
            </button>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 px-2 py-4 bg-white">
            {navigation.map((item) => (
              <button
                key={item.name}
                onClick={() => handleNavigation(item.page)}
                className={`group flex items-center w-full text-left px-2 py-2 text-sm font-medium rounded-md ${
                  isActive(item.page)
                    ? 'bg-blue-50 text-blue-700 border-blue-200 border-l-4 pl-5'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 mx-1'
                }`}
              >
                <span className="mr-3 text-lg">{item.icon}</span>
                {item.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Main content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top navigation */}
          <header className="bg-white shadow-sm border-b border-gray-200">
            <div className="px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between h-16">
                <div className="flex items-center">
                  <button
                    onClick={() => setSidebarOpen(true)}
                    className="lg:hidden p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <Bars3Icon className="h-6 w-6" />
                  </button>
                  <div className="hidden lg:block">
                    <h2 className="text-lg font-semibold text-gray-900">
                      {getPageTitle()}
                    </h2>
                  </div>
                </div>
                <div className="flex items-center">
                  <div className="text-sm text-gray-500 mr-4 hidden sm:block">
                    Admin Mode
                  </div>
                  <div className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                    Online
                  </div>
                </div>
              </div>
            </div>
          </header>

          {/* Page content */}
          <main className="flex-1 overflow-y-auto bg-gray-50">
            <div className="px-4 sm:px-6 lg:px-8 py-8">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
