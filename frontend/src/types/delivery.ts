/**
 * Delivery Slot TypeScript Interfaces.
 *
 * Ref: Backend delivery slot model
 */

import type { UUID } from './common';

export interface DeliverySlot {
  id: string;
  date: string; // YYYY-MM-DD
  start_time: string; // HH:MM
  end_time: string; // HH:MM
  max_capacity: number;
  current_count: number;
  available_count: number;
  is_active: boolean;
  is_almost_full: boolean;
}

export interface DeliverySlotDetailResponse {
  success: boolean;
  data: DeliverySlot;
}

export interface AvailableSlotsResponse {
  success: boolean;
  data: {
    slots: DeliverySlot[];
    count: number;
    start_date: string;
    end_date: string;
  };
}

export interface BatchCreateSlotsRequest {
  start_date: string;
  days: number;
  time_slots?: Array<[string, string]>;
  capacity: number;
}

export interface BatchCreateSlotsResponse {
  success: boolean;
  data: {
    slots: DeliverySlot[];
    count: number;
  };
}

export interface EmergencyBlockRequest {
  reason?: string;
}

export interface EmergencyBlockResponse {
  success: boolean;
  data: {
    slot_id: UUID;
    status: string;
    reason: string;
  };
}
