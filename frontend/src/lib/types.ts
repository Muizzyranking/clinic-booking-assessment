// Mirrors the backend's pydantic schemas (backend/app/schemas.py).

export type BookingStatus = "confirmed" | "cancelled";

export interface Slot {
  id: string;
  provider: string;
  start: string;
  end: string;
  available: boolean;
}

export interface NewSlot {
  id: string;
  provider: string;
  start: string;
  end: string;
}

export interface SlotsResponse {
  slots: Slot[];
}

export interface NewBooking {
  slot_id: string;
  name: string;
  email: string;
}

export interface Booking {
  id: string;
  slot_id: string;
  name: string;
  email: string;
  status: BookingStatus;
  created_at: string;
}

export interface BookingPage {
  bookings: Booking[];
  next_cursor: string | null;
}

export interface ErrorBody {
  error: string;
}
