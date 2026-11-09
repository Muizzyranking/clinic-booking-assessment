import { useEffect, useState } from "react";

const SLOTS = [
  { time: "9:00", provider: "Dr Chioma Okafor" },
  { time: "9:30", provider: "Dr Chioma Okafor" },
  { time: "10:00", provider: "Dr Musa Bello" },
  { time: "10:30", provider: "Dr Musa Bello" },
];

/** A small live picture of the product: pick a slot, then see it confirmed. */
export function HeroWindow() {
  const [picked, setPicked] = useState(0);
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setPicked(1);
      setConfirmed(true);
      return;
    }
    // One loop of 3.6 s: pick, then confirm, then start again.
    const steps = [
      () => {
        setConfirmed(false);
        setPicked((value) => (value + 1) % SLOTS.length);
      },
      () => setConfirmed(true),
    ];
    let step = 0;
    const timer = window.setInterval(() => {
      steps[step]?.();
      step = (step + 1) % steps.length;
    }, 1800);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="window" role="img" aria-label="Booking screen: four free slots, one picked and confirmed">
      <div className="window__bar">
        <span className="window__dot" />
        <span className="window__dot" />
        <span className="window__dot" />
        <span className="window__title">Slots, Thursday 10 December</span>
      </div>
      <div className="window__body">
        <ul className="window__slots">
          {SLOTS.map((slot, index) => (
            <li
              key={slot.time}
              className={index === picked ? "wslot is-picked" : "wslot"}
            >
              <b>{slot.time}</b>
              <span>{slot.provider}</span>
            </li>
          ))}
        </ul>
        <div className={confirmed ? "window__result is-on" : "window__result"}>
          <span className="window__check" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M5 12.5l4.5 4.5L19 7.5" />
            </svg>
          </span>
          <div>
            <b>Booking confirmed</b>
            <span>
              {SLOTS[picked]?.time} with {SLOTS[picked]?.provider}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
