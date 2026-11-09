import { Link } from "react-router-dom";

export function Logo() {
  return (
    <Link to="/" className="logo" aria-label="Clinic Booking, home">
      <svg className="logo__mark" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="4" width="18" height="4" rx="2" className="logo__bar logo__bar--accent" />
        <rect x="5" y="10" width="14" height="4" rx="2" className="logo__bar" />
        <rect x="3" y="16" width="18" height="4" rx="2" className="logo__bar" />
      </svg>
      <span>Clinic Booking</span>
    </Link>
  );
}
