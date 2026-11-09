import { useMemo, useState } from "react";

import { Select } from "./Select";
import { dayKey, formatDayShort, formatTime, hasStarted } from "../lib/format";
import type { Slot } from "../lib/types";

interface Props {
  slots: Slot[] | null;
  error: string | null;
  selectedId: string | null;
  onSelect: (slot: Slot) => void;
  onLoadSamples: () => void;
}

const isFree = (slot: Slot): boolean => slot.available && !hasStarted(slot);

const byStart = (a: Slot, b: Slot): number =>
  Date.parse(a.start) - Date.parse(b.start) || a.provider.localeCompare(b.provider);

interface Day {
  key: string;
  firstStart: string;
  free: number;
}

/**
 * Hundreds of slots stay usable by narrowing in two steps: pick a doctor (or
 * all of them), pick a day, then choose a time. Times are grouped by doctor.
 */
export function SlotBrowser({ slots, error, selectedId, onSelect, onLoadSamples }: Props) {
  const [provider, setProvider] = useState("");
  const [chosenDay, setChosenDay] = useState<string | null>(null);

  const sorted = useMemo(() => (slots ? [...slots].sort(byStart) : []), [slots]);
  const providers = useMemo(
    () => [...new Set(sorted.map((slot) => slot.provider))].sort((a, b) => a.localeCompare(b)),
    [sorted],
  );
  // A doctor from before a reseed may no longer exist: fall back to everyone.
  const activeProvider = providers.includes(provider) ? provider : "";

  const visible = useMemo(
    () => (activeProvider ? sorted.filter((slot) => slot.provider === activeProvider) : sorted),
    [sorted, activeProvider],
  );

  const days = useMemo<Day[]>(() => {
    const found = new Map<string, Day>();
    for (const slot of visible) {
      const key = dayKey(slot.start);
      const day = found.get(key) ?? { key, firstStart: slot.start, free: 0 };
      if (isFree(slot)) day.free += 1;
      found.set(key, day);
    }
    return [...found.values()];
  }, [visible]);

  const activeDay =
    days.find((day) => day.key === chosenDay)?.key ??
    days.find((day) => day.free > 0)?.key ??
    days[0]?.key ??
    null;

  const groups = useMemo(() => {
    const byDoctor = new Map<string, Slot[]>();
    for (const slot of visible) {
      if (dayKey(slot.start) !== activeDay) continue;
      byDoctor.set(slot.provider, [...(byDoctor.get(slot.provider) ?? []), slot]);
    }
    return [...byDoctor.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [visible, activeDay]);

  if (error) {
    return (
      <p className="form-error" role="alert">
        {error}
      </p>
    );
  }

  if (slots === null) {
    return (
      <div className="skeletons" aria-busy="true" aria-label="Loading slots">
        {[0, 1, 2, 3].map((item) => (
          <span className="skeleton" key={item} />
        ))}
      </div>
    );
  }

  if (slots.length === 0) {
    return (
      <div className="empty">
        <p>No slots yet. Generate random doctors, slots and bookings to try the flow.</p>
        <button type="button" className="btn btn--secondary btn--small" onClick={onLoadSamples}>
          Generate sample data
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="filters">
        <Select
          label="Doctor"
          value={activeProvider}
          onChange={setProvider}
          options={[
            { value: "", label: `All doctors (${providers.length})` },
            ...providers.map((name) => ({ value: name, label: name })),
          ]}
        />
      </div>

      <div className="chips" role="group" aria-label="Choose a day">
        {days.map((day) => (
          <button
            type="button"
            key={day.key}
            className={day.key === activeDay ? "chip is-active" : "chip"}
            aria-pressed={day.key === activeDay}
            onClick={() => setChosenDay(day.key)}
          >
            <b>{formatDayShort(day.firstStart)}</b>
            <span>{day.free} free</span>
          </button>
        ))}
      </div>

      {groups.length === 0 && <p className="muted-text">No slots on this day.</p>}
      {groups.map(([name, list]) => (
        <div className="doctor" key={name}>
          <h3>
            {name}
            <span>{list.filter(isFree).length} free</span>
          </h3>
          <ul className="time-grid">
            {list.map((slot) => {
              const free = isFree(slot);
              const state = hasStarted(slot) ? "already started" : slot.available ? "free" : "booked";
              return (
                <li key={slot.id}>
                  <button
                    type="button"
                    className={slot.id === selectedId ? "time is-selected" : "time"}
                    disabled={!free}
                    aria-pressed={slot.id === selectedId}
                    aria-label={`${formatTime(slot.start)} with ${name}, ${state}`}
                    onClick={() => onSelect(slot)}
                  >
                    {formatTime(slot.start)}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}

      <div className="panel__foot">
        <button type="button" className="btn btn--ghost btn--small" onClick={onLoadSamples}>
          Replace with new sample data
        </button>
      </div>
    </>
  );
}
