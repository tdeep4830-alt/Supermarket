/**
 * Admin Delivery Slots Management Page.
 *
 * Allows administrators to manage delivery slots, including:
 * - Batch creation of slots
 * - Emergency blocking of slots
 * - Viewing slot status
 */

import { useState, useCallback } from 'react';
import { AdminLayout } from '../components/AdminLayout';
import { PlusCircleIcon, ExclamationTriangleIcon, CalendarDaysIcon, CircleStackIcon } from '@heroicons/react/24/outline';
import type { DeliverySlot } from '@/types';
import {
  useDeliverySlots,
  useBatchCreateSlots,
  useEmergencyBlockSlot,
} from '../hooks/useDeliverySlots';
import { useAddToast } from '@/store/toastStore';

interface BatchCreateForm {
  start_date: string;
  days: number;
  capacity: number;
}

export function DeliverySlotsPage(): JSX.Element {
  const addToast = useAddToast();
  const [showBatchCreateModal, setShowBatchCreateModal] = useState(false);
  const [batchForm, setBatchForm] = useState<BatchCreateForm>({
    start_date: '',
    days: 7,
    capacity: 10,
  });
  const [selectedSlots, setSelectedSlots] = useState<Set<string>>(new Set());

  // Fetch delivery slots
  const { data: slotsResponse, isLoading } = useDeliverySlots();
  const slots: DeliverySlot[] = slotsResponse?.data || [];

  // Mutations
  const batchCreateMutation = useBatchCreateSlots(
    () => {
      addToast({
        type: 'success',
        message: '配送時段批次建立成功！',
      });
      setShowBatchCreateModal(false);
    },
    (error) => {
      addToast({
        type: 'error',
        message: '批次建立失敗：' + error.message,
      });
    }
  );

  const emergencyBlockMutation = useEmergencyBlockSlot(
    () => {
      addToast({
        type: 'success',
        message: '緊急下架成功！',
      });
      setSelectedSlots(new Set()); // Clear selection
    },
    (error) => {
      addToast({
        type: 'error',
        message: '緊急下架失敗：' + error.message,
      });
    }
  );

  const handleBatchCreate = useCallback(() => {
    if (!batchForm.start_date || batchForm.days < 1) {
      addToast({
        type: 'warning',
        message: '請填寫完整資訊',
      });
      return;
    }

    batchCreateMutation.mutate({
      start_date: batchForm.start_date,
      days: batchForm.days,
      capacity: batchForm.capacity,
    });
  }, [batchForm, batchCreateMutation, addToast]);

  const handleEmergencyBlock = useCallback(() => {
    if (selectedSlots.size === 0) {
      addToast({
        type: 'warning',
        message: '請選擇要下架的配送時段',
      });
      return;
    }

    selectedSlots.forEach(slotId => {
      emergencyBlockMutation.mutate({
        slotId,
        reason: '緊急下架',
      });
    });
  }, [selectedSlots, emergencyBlockMutation, addToast]);

  const toggleSlotSelection = (slotId: string) => {
    setSelectedSlots(prev => {
      const newSet = new Set(prev);
      if (newSet.has(slotId)) {
        newSet.delete(slotId);
      } else {
        newSet.add(slotId);
      }
      return newSet;
    });
  };

  const getSlotStatus = (slot: DeliverySlot) => {
    if (!slot.is_active) {
      return { label: '已下架', color: 'bg-gray-100 text-gray-800 border-gray-200' };
    }
    if (slot.current_count >= slot.max_capacity) {
      return { label: '已滿', color: 'bg-red-100 text-red-800 border-red-200' };
    }
    if (slot.is_almost_full) {
      return { label: '即將額滿', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' };
    }
    return { label: '可預約', color: 'bg-green-100 text-green-800 border-green-200' };
  };

  const getUtilizationRate = (slot: DeliverySlot) => {
    return Math.round((slot.current_count / slot.max_capacity) * 100);
  };

  // Sort slots by date and time
  const sortedSlots = [...slots].sort((a, b) => {
    if (a.date !== b.date) {
      return a.date.localeCompare(b.date);
    }
    return a.start_time.localeCompare(b.start_time);
  });

  // Group by date for display
  const groupedByDate = sortedSlots.reduce((acc, slot) => {
    if (!acc[slot.date]) {
      acc[slot.date] = [];
    }
    acc[slot.date].push(slot);
    return acc;
  }, {} as Record<string, DeliverySlot[]>);

  return (
    <AdminLayout currentPage="delivery-slots">
      <div className="space-y-6">
        {/* Header */}
        <div className="md:flex md:items-center md:justify-between">
          <div className="min-w-0 flex-1">
            <h2 className="text-2xl font-bold leading-7 text-foreground sm:truncate sm:text-3xl">
              配送時段管理
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              管理和建立配送時段，確保顧客能順利預約配送服務。
            </p>
          </div>
          <div className="mt-4 md:mt-0 flex gap-2">
            <button
              type="button"
              onClick={() => setShowBatchCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
            >
              <PlusCircleIcon className="-ml-1 mr-2 h-4 w-4" />
              批次建立時段
            </button>
            <button
              type="button"
              onClick={handleEmergencyBlock}
              disabled={selectedSlots.size === 0 || emergencyBlockMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-destructive-foreground bg-destructive hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-destructive"
            >
              <ExclamationTriangleIcon className="-ml-1 mr-2 h-4 w-4" />
              緊急下架 ({selectedSlots.size})
            </button>
          </div>
        </div>

        {/* Info Panel */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <CircleStackIcon className="h-5 w-5 text-blue-400" />
            </div>
            <div className="ml-3 flex-1">
              <div className="text-sm text-blue-700">
                <p className="font-semibold">配送時段管理須知</p>
                <ul className="mt-2 list-disc list-inside space-y-1">
                  <li>可選取多個時段進行緊急下架</li>
                  <li>使用批次建立功能快速建立下週的配送時段</li>
                  <li>被冷凍的時段將不再顯示給顧客</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="text-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-500 mx-auto"></div>
            <p className="mt-2 text-muted-foreground">載入中...</p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && sortedSlots.length === 0 && (
          <div className="text-center bg-card border border-border rounded-lg p-8">
            <CalendarDaysIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">尚無配送時段</h3>
            <p className="text-muted-foreground mb-4">
              點擊「批次建立時段」按鈕開始建立配送時段
            </p>
            <button
              type="button"
              onClick={() => setShowBatchCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90"
            >
              <PlusCircleIcon className="-ml-1 mr-2 h-4 w-4" />
              批次建立時段
            </button>
          </div>
        )}

        {/* Slots List */}
        {!isLoading && sortedSlots.length > 0 && (
          <div className="space-y-6">
            {Object.entries(groupedByDate).map(([date, dateSlots]) => (
              <div key={date} className="bg-card border border-border rounded-lg">
                <div className="px-4 py-3 border-b border-border">
                  <h3 className="font-semibold text-foreground">
                    {new Date(date).toLocaleDateString('zh-TW', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      weekday: 'long',
                    })}
                  </h3>
                </div>
                <div className="divide-y divide-border">
                  {dateSlots.map((slot) => {
                    const status = getSlotStatus(slot);
                    const isSelected = selectedSlots.has(slot.id);

                    return (
                      <div
                        key={slot.id}
                        className={`p-4 transition-colors ${
                          !slot.is_active ? 'bg-muted/50' : ''
                        } hover:bg-accent/50`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSlotSelection(slot.id)}
                              className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
                              disabled={!slot.is_active}
                            />
                            <div>
                              <div className="font-medium text-foreground">
                                {slot.start_time} - {slot.end_time}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                {slot.current_count} / {slot.max_capacity} 個預約
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-24 bg-secondary rounded-full h-2 overflow-hidden">
                              <div
                                className="h-full bg-primary transition-all"
                                style={{
                                  width: `${getUtilizationRate(slot)}%`,
                                }}
                              />
                            </div>
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${status.color}`}
                            >
                              {status.label}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Batch Create Modal */}
        {showBatchCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-card border border-border rounded-lg p-6 max-w-md w-full mx-4">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                批次建立配送時段
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    開始日期
                  </label>
                  <input
                    type="date"
                    value={batchForm.start_date}
                    onChange={(e) => setBatchForm({ ...batchForm, start_date: e.target.value })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    建立天數
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={batchForm.days}
                    onChange={(e) => setBatchForm({ ...batchForm, days: parseInt(e.target.value) || 1 })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    每時段最大容量
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={batchForm.capacity}
                    onChange={(e) => setBatchForm({ ...batchForm, capacity: parseInt(e.target.value) || 10 })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    required
                  />
                </div>
                <div className="text-sm text-muted-foreground">
                  將建立 {batchForm.days} 天的配送時段，每天 3 個時段 (09:00-12:00, 14:00-17:00, 18:00-21:00)
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => setShowBatchCreateModal(false)}
                  className="px-4 py-2 text-sm font-medium rounded-md border border-input bg-background hover:bg-accent"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={handleBatchCreate}
                  disabled={batchCreateMutation.isPending || !batchForm.start_date}
                  className="px-4 py-2 text-sm font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {batchCreateMutation.isPending ? '建立中...' : '建立'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}