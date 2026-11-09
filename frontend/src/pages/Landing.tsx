import { Link } from "react-router-dom";

import { HeroWindow } from "../components/HeroWindow";
import { Logo } from "../components/Logo";
import { StatementMoment } from "../components/StatementMoment";
import { DOCS_URL } from "../lib/api";

const STEPS = [
  {
    title: "Pick a free slot",
    body: "Each slot shows the doctor, the time and whether it is taken.",
  },
  {
    title: "Enter name and email",
    body: "Both are required. Emails are checked and stored in lower case.",
  },
  {
    title: "Get a confirmation",
    body: "The booking comes back with an ID that staff can look up or cancel.",
  },
];

const RULES = [
  {
    title: "Blocks double bookings",
    body: "Two patients can never take the same slot, even in the same instant.",
  },
  {
    title: "Rejects bad details",
    body: "Missing names, broken emails and slots that already started are turned away.",
  },
  {
    title: "Ignores repeated requests",
    body: "A retry with the same key returns the first booking, never a second one.",
  },
  {
    title: "Limits repeat attempts",
    body: "Five tries a minute per email, failed ones included, then a wait time.",
  },
];

const STATEMENT = "Cancel a booking and its slot is free again, ready for the next patient.".split(" ");

export function Landing() {
  return (
    <>
      <a className="skip-link" href="#top">
        Skip to content
      </a>
      <header className="nav">
        <div className="wrap nav__row">
          <Logo />
          <nav className="nav__links" aria-label="Sections">
            <a href="#booking">Booking</a>
            <a href="#rules">Rules</a>
            <a href="#cancel">Cancel</a>
            <a href={DOCS_URL} target="_blank" rel="noreferrer">
              API docs
            </a>
          </nav>
          <Link className="btn btn--primary" to="/dashboard">
            Open the dashboard
          </Link>
        </div>
      </header>

      <main id="top">
        <section className="hero" data-enter>
          <div className="wrap hero__inner">
            <h1 className="enter" style={{ "--i": 0 } as React.CSSProperties}>
              Appointment booking for clinics
            </h1>
            <p className="hero__lead enter" style={{ "--i": 1 } as React.CSSProperties}>
              Patients pick a free slot and get a confirmation straight away. Staff see every
              booking in one dashboard and cancel in a click.
            </p>
            <div className="btn-row enter" style={{ "--i": 2 } as React.CSSProperties}>
              <Link className="btn btn--primary" to="/dashboard">
                Open the dashboard
              </Link>
              <a className="btn btn--secondary" href="#booking">
                See how booking works
              </a>
            </div>
            <div className="hero__frame enter" style={{ "--i": 3 } as React.CSSProperties}>
              <HeroWindow />
            </div>
          </div>
        </section>

        <section className="section" id="booking">
          <div className="wrap">
            <h2>
              Booking in three steps. <span className="muted">No account needed.</span>
            </h2>
            <ol className="cards cards--3">
              {STEPS.map((step, index) => (
                <li className="card" key={step.title}>
                  <span className="card__index">0{index + 1}</span>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="section section--alt" id="cancel">
          <div className="wrap">
            <h2 className="visually-hidden">Cancelling a booking</h2>
            <StatementMoment words={STATEMENT} strong={[0, 7, 8]} />
          </div>
        </section>

        <section className="section" id="rules">
          <div className="wrap">
            <h2>
              Rules the booking enforces. <span className="muted">On every request.</span>
            </h2>
            <ul className="cards cards--2">
              {RULES.map((rule) => (
                <li className="card" key={rule.title}>
                  <h3>{rule.title}</h3>
                  <p>{rule.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="section close">
          <div className="wrap close__inner">
            <h2>Manage slots and bookings</h2>
            <p>Enter your API key to see the slots, book one and cancel it.</p>
            <Link className="btn btn--primary" to="/dashboard">
              Open the dashboard
            </Link>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="wrap footer__row">
          <Logo />
          <span className="footer__legal">Clinic Booking, {new Date().getFullYear()}</span>
        </div>
      </footer>
    </>
  );
}
