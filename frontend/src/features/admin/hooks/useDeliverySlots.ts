/**
 * Delivery Slots API Hooks for Admin.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/client';
import type { DeliverySlot } from '@/types';

interface BatchCreateSlotsPayload {
  start_date: string;
  days: number;
  time_slots?: Array<[string, string]>;
  capacity: number;
}

interface EmergencyBlockPayload {
  reason?: string;
}

interface BatchCreateResponse {
  success: boolean;
  message: string;
  data: {
    slots: DeliverySlot[];
    count: number;
  };
}

interface EmergencyBlockResponse {
  success: boolean;
  message: string;
  data: {
    slot_id: string;
    status: string;
    reason: string;
  };
}

export function useDeliverySlots() {
  return useQuery({
    queryKey: ['delivery-slots'],
    queryFn: async () => {
      const response = await apiClient.get('/delivery/admin/slots/');
      return response.data;
    },
    staleTime: 0, // Always fresh for admin view
  });
}

export function useBatchCreateSlots(onSuccess?: () => void, onError?: (error: Error) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BatchCreateSlotsPayload) => {
      const response = await apiClient.post<
        BatchCreateResponse,
        BatchCreateResponse,
        BatchCreateSlotsPayload
      >('/delivery/admin/slots/batch-create/', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery-slots'] });
      onSuccess?.();
    },
    onError: (error) => {
      onError?.(error);
    },
  });
}

export function useEmergencyBlockSlot(onSuccess?: () => void, onError?: (error: Error) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ slotId, reason }: { slotId: string; reason?: string }) => {
      const response = await apiClient.patch<EmergencyBlockResponse>(
        `/delivery/admin/slots/${slotId}/emergency-block/`,
        { reason }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delivery-slots'] });
      onSuccess?.();
    },
    onError: (error) => {
      onError?.(error);
    },
  });
}
