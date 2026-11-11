import { useEffect, useState } from "react";

const STEPS = ["Reading your resume", "Scouting your skills", "Comparing you with the role", "Checking the evidence", "Printing your card"];

export default function LoadingCard({ serverWaking }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const step = STEPS[Math.min(STEPS.length - 1, Math.floor(seconds / 4))];

  return (
    <section className="loading" aria-live="polite" aria-busy="true">
      <div className="card-frame skeleton" aria-hidden="true">
        <div className="card-inner shimmer" />
      </div>
      <div className="loading-text">
        <p className="loading-step">{step}…</p>
        <p className="muted">{seconds}s</p>
        {(serverWaking || seconds > 15) && (
          <p className="muted small">
            The free server naps when nobody's using it. The first card can take up to a minute; after that it's
            much faster.
          </p>
        )}
      </div>
    </section>
  );
}
