import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth";
import { BookingDetails } from "../components/BookingDetails";
import { useConfirm } from "../components/ConfirmDialog";
import { Logo } from "../components/Logo";
import { SlotBrowser } from "../components/SlotBrowser";
import { ApiError, DOCS_URL, createApi, errorMessage, type Api } from "../lib/api";
import { formatStamp } from "../lib/format";
import type { Booking, Slot } from "../lib/types";

export function Dashboard() {
  const { api, signOut } = useAuth();

  return (
    <div className="app">
      <header className="nav nav--app">
        <div className="wrap nav__row">
          <Logo />
          <div className="nav__actions">
            <a className="btn btn--ghost btn--small" href={DOCS_URL} target="_blank" rel="noreferrer">
              API docs
            </a>
            {api ? (
              <button type="button" className="btn btn--secondary btn--small" onClick={signOut}>
                Lock dashboard
              </button>
            ) : (
              <Link className="btn btn--secondary btn--small" to="/">
                Back to home
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="wrap app__main">
        {api ? <Workspace api={api} onLocked={signOut} /> : <KeyGate />}
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ gate */

function KeyGate() {
  const { signIn } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [shake, setShake] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const key = value.trim();
    if (!key) {
      setError("Enter your API key to continue.");
      return;
    }
    setChecking(true);
    setError(null);
    try {
      await createApi(key).listSlots();
      signIn(key);
    } catch (caught) {
      setError(
        caught instanceof ApiError && caught.status === 401
          ? "That key was not accepted. Check it and try again."
          : errorMessage(caught),
      );
      setShake(true);
      window.setTimeout(() => setShake(false), 400);
    } finally {
      setChecking(false);
    }
  }

  return (
    <section className="gate">
      <form className={shake ? "gate__card is-shaking" : "gate__card"} onSubmit={submit} noValidate>
        <span className="gate__lock" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <rect x="5" y="11" width="14" height="9" rx="2.5" />
            <path d="M8 11V8a4 4 0 0 1 8 0v3" />
          </svg>
        </span>
        <h1>Dashboard</h1>
        <p className="gate__hint" id="key-hint">
          Hint: enter your API key
        </p>
        <label className="field">
          <span className="field__label">API key</span>
          <input
            type="password"
            autoComplete="current-password"
            autoFocus
            value={value}
            onChange={(event) => setValue(event.target.value)}
            aria-describedby="key-hint key-error"
            aria-invalid={error !== null}
          />
        </label>
        <p className="form-error" id="key-error" role="alert" hidden={error === null}>
          {error}
        </p>
        <button type="submit" className="btn btn--primary btn--block" disabled={checking}>
          {checking ? "Checking…" : "Unlock dashboard"}
        </button>
      </form>
    </section>
  );
}

/* ------------------------------------------------------------- workspace */

function Workspace({ api, onLocked }: { api: Api; onLocked: () => void }) {
  const confirm = useConfirm();
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Slot | null>(null);
  const [confirmation, setConfirmation] = useState<Booking | null>(null);
  const [lookupEmail, setLookupEmail] = useState<string | null>(null);
  const [lookupVersion, setLookupVersion] = useState(0);

  const refresh = useCallback(async () => {
    try {
      setSlots(await api.listSlots());
      setLoadError(null);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        onLocked();
        return;
      }
      setLoadError(errorMessage(caught));
    }
  }, [api, onLocked]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function loadSamples() {
    const yes = await confirm({
      title: "Replace with new sample data?",
      message: "This clears every slot and booking and generates a fresh random set.",
      confirmLabel: "Replace everything",
      cancelLabel: "Keep current data",
      tone: "danger",
    });
    if (!yes) return;
    try {
      setSlots(await api.seedSlots());
      setSelected(null);
      setConfirmation(null);
      setLookupVersion((value) => value + 1);
    } catch (caught) {
      setLoadError(errorMessage(caught));
    }
  }

  function booked(booking: Booking) {
    setConfirmation(booking);
    setSelected(null);
    setLookupEmail(booking.email);
    setLookupVersion((value) => value + 1);
    void refresh();
  }

  function cancelled(booking: Booking) {
    setConfirmation((current) => (current?.id === booking.id ? booking : current));
    setLookupVersion((value) => value + 1);
    void refresh();
  }

  return (
    <div className="grid">
      <section className="panel panel--slots" aria-labelledby="slots-title">
        <div className="panel__head">
          <h2 id="slots-title">Available slots</h2>
          <button type="button" className="btn btn--ghost btn--small" onClick={() => void refresh()}>
            Refresh
          </button>
        </div>
        <SlotBrowser
          slots={slots}
          error={loadError}
          selectedId={selected?.id ?? null}
          onSelect={(slot) => {
            setSelected(slot);
            setConfirmation(null);
          }}
          onLoadSamples={loadSamples}
        />
      </section>

      <div className="stack">
        {confirmation ? (
          <Confirmation
            booking={confirmation}
            slot={slots?.find((slot) => slot.id === confirmation.slot_id) ?? null}
            api={api}
            onCancelled={cancelled}
            onDismiss={() => setConfirmation(null)}
          />
        ) : (
          <BookingForm
            key={selected?.id ?? "none"}
            api={api}
            slot={selected}
            onBooked={booked}
            onSlotTaken={() => void refresh()}
          />
        )}
        <Lookup
          api={api}
          slots={slots}
          initialEmail={lookupEmail}
          version={lookupVersion}
          onCancelled={cancelled}
        />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ book a slot */

interface BookingFormProps {
  api: Api;
  slot: Slot | null;
  onBooked: (booking: Booking) => void;
  onSlotTaken: () => void;
}

function BookingForm({ api, slot, onBooked, onSlotTaken }: BookingFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Same details, same key: a retry or double click can never book twice.
  const [attempt, setAttempt] = useState<{ body: string; key: string } | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!slot) return;
    const body = { slot_id: slot.id, name: name.trim(), email: email.trim() };
    const serialised = JSON.stringify(body);
    const key = attempt?.body === serialised ? attempt.key : crypto.randomUUID();
    setAttempt({ body: serialised, key });
    setBusy(true);
    setError(null);
    try {
      onBooked(await api.createBooking(body, key));
    } catch (caught) {
      setError(errorMessage(caught));
      if (caught instanceof ApiError && caught.status === 409) onSlotTaken();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-labelledby="book-title">
      <h2 id="book-title">Book a slot</h2>
      {slot ? (
        <form onSubmit={submit} className="form" noValidate>
          <p className="chosen">
            <b>{slot.provider}</b> · {formatStamp(slot.start)}
          </p>
          <label className="field">
            <span className="field__label">Full name</span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoComplete="name"
              required
            />
          </label>
          <label className="field">
            <span className="field__label">Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <p className="form-error" role="alert" hidden={error === null}>
            {error}
          </p>
          <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
            {busy ? "Booking…" : "Confirm booking"}
          </button>
        </form>
      ) : (
        <p className="muted-text">Pick a free slot on the left to start.</p>
      )}
    </section>
  );
}

/* ----------------------------------------------------------- confirmation */

interface ConfirmationProps {
  booking: Booking;
  slot: Slot | null;
  api: Api;
  onCancelled: (booking: Booking) => void;
  onDismiss: () => void;
}

function Confirmation({ booking, slot, api, onCancelled, onDismiss }: ConfirmationProps) {
  const confirm = useConfirm();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isCancelled = booking.status === "cancelled";

  async function cancel() {
    const yes = await confirm({
      title: "Cancel this booking?",
      message: "The slot opens up again for someone else.",
      confirmLabel: "Cancel booking",
      cancelLabel: "Keep it",
      tone: "danger",
    });
    if (!yes) return;
    setBusy(true);
    setError(null);
    try {
      onCancelled(await api.cancelBooking(booking.id));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel confirm" aria-live="polite" aria-labelledby="confirm-title">
      <div className={isCancelled ? "confirm__badge is-cancelled" : "confirm__badge"}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          {isCancelled ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M5 12.5l4.5 4.5L19 7.5" />}
        </svg>
      </div>
      <h2 id="confirm-title">{isCancelled ? "Booking cancelled" : "Booking confirmed"}</h2>
      <dl className="facts">
        <dt>Booking ID</dt>
        <dd className="mono">{booking.id}</dd>
        <dt>When</dt>
        <dd>{slot ? `${formatStamp(slot.start)} with ${slot.provider}` : booking.slot_id}</dd>
        <dt>Patient</dt>
        <dd>{booking.name}</dd>
        <dt>Email</dt>
        <dd>{booking.email}</dd>
      </dl>
      <p className="form-error" role="alert" hidden={error === null}>
        {error}
      </p>
      <div className="btn-row">
        {!isCancelled && (
          <button type="button" className="btn btn--danger btn--small" onClick={cancel} disabled={busy}>
            {busy ? "Cancelling…" : "Cancel booking"}
          </button>
        )}
        <button type="button" className="btn btn--secondary btn--small" onClick={onDismiss}>
          Book another
        </button>
      </div>
    </section>
  );
}

/* ----------------------------------------------------------------- lookup */

type LookupMode = "email" | "id";

interface Query {
  mode: LookupMode;
  value: string;
}

interface LookupProps {
  api: Api;
  slots: Slot[] | null;
  initialEmail: string | null;
  /** Bumped whenever bookings change elsewhere, to reload the list. */
  version: number;
  onCancelled: (booking: Booking) => void;
}

function Lookup({ api, slots, initialEmail, version, onCancelled }: LookupProps) {
  const confirm = useConfirm();
  const [mode, setMode] = useState<LookupMode>("email");
  const [input, setInput] = useState(initialEmail ?? "");
  const [query, setQuery] = useState<Query | null>(
    initialEmail ? { mode: "email", value: initialEmail } : null,
  );
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opened, setOpened] = useState<Booking | null>(null);

  useEffect(() => {
    if (initialEmail) {
      setMode("email");
      setInput(initialEmail);
      setQuery({ mode: "email", value: initialEmail });
    }
  }, [initialEmail]);

  useEffect(() => {
    if (!query) return;
    let ignore = false;
    setLoading(true);
    setError(null);
    const found =
      query.mode === "email"
        ? api.listBookings(query.value)
        : api
            .getBooking(query.value)
            .then((booking) => ({ bookings: [booking], next_cursor: null }));
    found
      .then((page) => {
        if (ignore) return;
        setBookings(page.bookings);
        setCursor(page.next_cursor);
      })
      .catch((caught: unknown) => {
        if (ignore) return;
        setBookings([]);
        setCursor(null);
        setError(errorMessage(caught));
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [api, query, version]);

  async function more() {
    if (query?.mode !== "email" || !cursor) return;
    setLoading(true);
    try {
      const page = await api.listBookings(query.value, cursor);
      setBookings((current) => [...current, ...page.bookings]);
      setCursor(page.next_cursor);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  async function cancel(booking: Booking) {
    const yes = await confirm({
      title: "Cancel this booking?",
      message: `${booking.name}'s appointment will be cancelled and the slot opens up again.`,
      confirmLabel: "Cancel booking",
      cancelLabel: "Keep it",
      tone: "danger",
    });
    if (!yes) return;
    try {
      onCancelled(await api.cancelBooking(booking.id));
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  function search(event: FormEvent) {
    event.preventDefault();
    const next = input.trim();
    if (next) setQuery({ mode, value: next });
  }

  function switchMode(next: LookupMode) {
    setMode(next);
    setInput("");
    setError(null);
  }

  function describe(booking: Booking): string {
    const slot = slots?.find((item) => item.id === booking.slot_id);
    return slot ? `${slot.provider} · ${formatStamp(slot.start)}` : booking.slot_id;
  }

  const openedSlot = opened ? (slots?.find((item) => item.id === opened.slot_id) ?? null) : null;

  return (
    <section className="panel" aria-labelledby="lookup-title">
      <h2 id="lookup-title">Find bookings</h2>
      <div className="segmented" role="group" aria-label="Search by">
        <button
          type="button"
          className={mode === "email" ? "is-active" : undefined}
          aria-pressed={mode === "email"}
          onClick={() => switchMode("email")}
        >
          Patient email
        </button>
        <button
          type="button"
          className={mode === "id" ? "is-active" : undefined}
          aria-pressed={mode === "id"}
          onClick={() => switchMode("id")}
        >
          Booking ID
        </button>
      </div>
      <form className="inline-form" onSubmit={search}>
        <label className="field field--grow">
          <span className="field__label">{mode === "email" ? "Patient email" : "Booking ID"}</span>
          <input
            key={mode}
            type={mode === "email" ? "email" : "text"}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <button type="submit" className="btn btn--secondary">
          Search
        </button>
      </form>
      <p className="form-error" role="alert" hidden={error === null}>
        {error}
      </p>
      {query?.mode === "email" && !loading && bookings.length === 0 && !error && (
        <p className="muted-text">No bookings for {query.value}.</p>
      )}
      <ul className="bookings">
        {bookings.map((booking) => (
          <li className="booking" key={booking.id}>
            <button
              type="button"
              className="booking__open"
              onClick={() => setOpened(booking)}
              aria-label={`View details for ${booking.name}, ${booking.status}`}
            >
              <span className="booking__text">
                <b>{booking.name}</b>
                <span className="mono">{describe(booking)}</span>
              </span>
              <span className={`status status--${booking.status}`}>{booking.status}</span>
              <svg className="booking__chevron" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M9.5 6l6 6-6 6" />
              </svg>
            </button>
            {booking.status === "confirmed" && (
              <button
                type="button"
                className="btn btn--ghost btn--small"
                onClick={() => void cancel(booking)}
              >
                Cancel
              </button>
            )}
          </li>
        ))}
      </ul>
      {cursor && (
        <button
          type="button"
          className="btn btn--secondary btn--small"
          onClick={() => void more()}
          disabled={loading}
        >
          {loading ? "Loading…" : "Load more"}
        </button>
      )}
      {opened && (
        <BookingDetails
          booking={opened}
          slot={openedSlot}
          api={api}
          onClose={() => setOpened(null)}
          onChanged={onCancelled}
        />
      )}
    </section>
  );
}
