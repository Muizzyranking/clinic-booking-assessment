import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

import { Dashboard } from "./pages/Dashboard";
import { Landing } from "./pages/Landing";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </>
  );
}
