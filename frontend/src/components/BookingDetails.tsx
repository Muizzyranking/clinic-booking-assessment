import { useEffect, useId, useState } from "react";

import { errorMessage, type Api } from "../lib/api";
import { formatCreated, formatFull, formatTime } from "../lib/format";
import type { Booking, Slot } from "../lib/types";
import { useConfirm } from "./ConfirmDialog";
import { Modal } from "./Modal";

interface Props {
  booking: Booking;
  /** The booked slot, when it is in the loaded list. */
  slot: Slot | null;
  api: Api;
  onClose: () => void;
  /** Called after the booking changes (cancelled) so lists can refresh. */
  onChanged: (booking: Booking) => void;
}

export function BookingDetails({ booking: initial, slot, api, onClose, onChanged }: Props) {
  const titleId = useId();
  const confirm = useConfirm();
  const [booking, setBooking] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const cancelled = booking.status === "cancelled";

  // The list row may be a moment old; show the current state.
  useEffect(() => {
    let ignore = false;
    api
      .getBooking(initial.id)
      .then((fresh) => {
        if (!ignore) setBooking(fresh);
      })
      .catch(() => undefined);
    return () => {
      ignore = true;
    };
  }, [api, initial.id]);

  async function copyId() {
    try {
      await navigator.clipboard.writeText(booking.id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setError("Couldn't copy. Select the ID and copy it by hand.");
    }
  }

  async function cancel() {
    const yes = await confirm({
      title: "Cancel this booking?",
      message: `${booking.name}'s appointment will be cancelled and the slot opens up again.`,
      confirmLabel: "Cancel booking",
      cancelLabel: "Keep it",
      tone: "danger",
    });
    if (!yes) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.cancelBooking(booking.id);
      setBooking(updated);
      onChanged(updated);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal labelledBy={titleId} onClose={onClose}>
      <div className="modal__head">
        <h2 id={titleId} className="modal__title">
          Booking details
        </h2>
        <span className={`status status--${booking.status}`}>{booking.status}</span>
      </div>

      <dl className="facts">
        <dt>Booking ID</dt>
        <dd className="mono id-row">
          <span>{booking.id}</span>
          <button type="button" className="btn btn--ghost btn--small" onClick={() => void copyId()}>
            {copied ? "Copied" : "Copy"}
          </button>
        </dd>
        {slot ? (
          <>
            <dt>Doctor</dt>
            <dd>{slot.provider}</dd>
            <dt>Date</dt>
            <dd>{formatFull(slot.start)}</dd>
            <dt>Time</dt>
            <dd>
              {formatTime(slot.start)} to {formatTime(slot.end)}
            </dd>
          </>
        ) : (
          <>
            <dt>Slot</dt>
            <dd className="mono">{booking.slot_id}</dd>
          </>
        )}
        <dt>Patient</dt>
        <dd>{booking.name}</dd>
        <dt>Email</dt>
        <dd>{booking.email}</dd>
        <dt>Booked on</dt>
        <dd>{formatCreated(booking.created_at)}</dd>
      </dl>

      <p className="form-error" role="alert" hidden={error === null}>
        {error}
      </p>

      <div className="modal__actions">
        {!cancelled && (
          <button type="button" className="btn btn--danger" onClick={() => void cancel()} disabled={busy}>
            {busy ? "Cancelling…" : "Cancel booking"}
          </button>
        )}
        <button type="button" className="btn btn--secondary" onClick={onClose}>
          Close
        </button>
      </div>
    </Modal>
  );
}
