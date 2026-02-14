/**
 * Delivery Slot Selector Component.
 *
 * Allows users to select a delivery slot during checkout.
 * Shows slots in a calendar/grid format with availability status.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { DeliverySlot } from '@/types';
import apiClient from '@/api/client';

interface DeliverySlotSelectorProps {
  selectedSlot: DeliverySlot | null;
  onSlotSelect: (slot: DeliverySlot) => void;
}

export function DeliverySlotSelector({
  selectedSlot,
  onSlotSelect,
}: DeliverySlotSelectorProps): JSX.Element {
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Fetch available delivery slots
  const { data: slotsResponse, isLoading, error } = useQuery({
    queryKey: ['delivery-slots'],
    queryFn: async () => {
      const response = await apiClient.get('/delivery/slots/available/');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const slots: DeliverySlot[] = slotsResponse?.data?.slots || [];

  // Group slots by date
  const groupedSlots = slots.reduce((acc, slot) => {
    const date = slot.date;
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(slot);
    return acc;
  }, {} as Record<string, DeliverySlot[]>);

  const sortedDates = Object.keys(groupedSlots).sort();

  // Auto-select first date if none selected
  const currentDate = selectedDate?.toISOString().split('T')[0];
  const activeDate = currentDate && groupedSlots[currentDate] ? currentDate : sortedDates[0];

  const handleDateSelect = (date: string) => {
    setSelectedDate(new Date(date));
    // Clear slot selection when changing dates
    if (selectedSlot && selectedSlot.date !== date) {
      // Parent component should handle this via props
    }
  };

  const getWeekday = (dateString: string) => {
    const date = new Date(dateString);
    const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
    return `週${weekdays[date.getDay()]}`;
  };

  const getDay = (dateString: string) => {
    const date = new Date(dateString);
    return date.getDate().toString();
  };

  const getSlotStatus = (slot: DeliverySlot) => {
    if (slot.current_count >= slot.max_capacity) {
      return { label: '已滿', color: 'bg-red-100 text-red-800 border-red-200' };
    }
    if (slot.is_almost_full) {
      return { label: '即將額滿', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' };
    }
    return { label: '可預約', color: 'bg-green-100 text-green-800 border-green-200' };
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <div className="flex gap-3">
          <svg className="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <p className="font-medium text-red-800">載入配送時段失敗</p>
            <p className="text-sm text-red-700 mt-1">{error.message}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="mb-4 font-semibold text-foreground">選擇配送時段</h3>

        {/* Date Tabs */}
        <div className="mb-4 flex gap-2 overflow-x-auto pb-2">
          {sortedDates.map((date) => {
            const isActive = date === activeDate;

            return (
              <button
                key={date}
                onClick={() => handleDateSelect(date)}
                className={`flex min-w-0 flex-col items-center rounded-lg border px-4 py-3 transition-all ${
                  isActive
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-card hover:bg-accent'
                }`}
              >
                <span className="text-xs">{getWeekday(date)}</span>
                <span className="text-lg font-semibold">{getDay(date)}</span>
              </button>
            );
          })}
        </div>

        {/* Time Slots Grid */}
        {activeDate && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {groupedSlots[activeDate].map((slot) => {
              const status = getSlotStatus(slot);
              const isSelected = selectedSlot?.id === slot.id;
              const isFull = slot.current_count >= slot.max_capacity;

              return (
                <button
                  key={slot.id}
                  onClick={() => !isFull && onSlotSelect(slot)}
                  disabled={isFull}
                  className={`rounded-lg border p-4 text-left transition-all ${
                    isFull
                      ? 'cursor-not-allowed opacity-50'
                      : 'cursor-pointer hover:border-primary hover:bg-accent'
                  } ${
                    isSelected
                      ? 'border-primary bg-primary/10'
                      : 'border-border bg-card'
                  }`}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-medium text-foreground">
                      {slot.start_time} - {slot.end_time}
                    </span>
                    <span
                      className={`rounded-full border px-2 py-1 text-xs font-medium ${status.color}`}
                    >
                      {status.label}
                    </span>
                  </div>

                  <div className="text-sm text-muted-foreground">
                    {slot.available_count} / {slot.max_capacity} 名額
                  </div>

                  {slot.is_almost_full && !isFull && (
                    <div className="mt-2 inline-flex items-center gap-1 text-xs text-yellow-600">
                      <svg
                        className="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        />
                      </svg>
                      僅剩 {slot.available_count} 個名額！
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {sortedDates.length === 0 && (
          <div className="rounded-lg border border-border bg-card p-8 text-center">
            <div className="mb-2 text-muted-foreground">暫無可用的配送時段</div>
            <p className="text-sm text-muted-foreground/70">
              請聯繫客服或稍後再試
            </p>
          </div>
        )}
      </div>
    </div>
  );
}