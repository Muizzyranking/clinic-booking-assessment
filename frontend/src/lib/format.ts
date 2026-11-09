import type { Slot } from "./types";

const dayFormat = new Intl.DateTimeFormat(undefined, {
  weekday: "long",
  day: "numeric",
  month: "long",
});
const timeFormat = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
const stampFormat = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
});

export const formatDay = (iso: string): string => dayFormat.format(new Date(iso));
export const formatTime = (iso: string): string => timeFormat.format(new Date(iso));
export const formatStamp = (iso: string): string => stampFormat.format(new Date(iso));

export const hasStarted = (slot: Pick<Slot, "start">): boolean =>
  new Date(slot.start).getTime() <= Date.now();

const dayKeyFormat = new Intl.DateTimeFormat("en-CA", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const dayShortFormat = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  day: "numeric",
  month: "short",
});

/** Local calendar date such as 2026-11-09, used to group slots by day. */
export const dayKey = (iso: string): string => dayKeyFormat.format(new Date(iso));
export const formatDayShort = (iso: string): string => dayShortFormat.format(new Date(iso));

const fullFormat = new Intl.DateTimeFormat(undefined, {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
});
const createdFormat = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

/** "Monday, 9 November 2026" */
export const formatFull = (iso: string): string => fullFormat.format(new Date(iso));
/** "9 November 2026 at 10:15 AM" style stamp for when something happened. */
export const formatCreated = (iso: string): string => createdFormat.format(new Date(iso));
