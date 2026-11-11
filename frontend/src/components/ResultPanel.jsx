import { useState } from "react";

const TABS = [
  { id: "stats", label: "Stats" },
  { id: "fit", label: "Job fit" },
  { id: "improve", label: "Improve" },
];

const band = (score) => (score >= 80 ? "elite" : score >= 70 ? "good" : score >= 60 ? "ok" : "low");

export default function ResultPanel({ card }) {
  const [tab, setTab] = useState("stats");

  return (
    <div className="panel result-panel">
      <p className="summary">{card.summary}</p>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`pane-${t.id}`}
            className={`tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`pane-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "stats" && <StatsTab card={card} />}
        {tab === "fit" && <FitTab card={card} />}
        {tab === "improve" && <ImproveTab card={card} />}
      </div>

      <HowItWorks card={card} />
    </div>
  );
}

function StatsTab({ card }) {
  return (
    <ul className="stat-list">
      {card.stats.map((s) => (
        <li key={s.key} className="stat-row">
          <div className="stat-head">
            <span className="stat-label">
              <span className="stat-code">{s.code}</span> {s.label}
            </span>
            <span className={`score score-${band(s.score)}`}>{s.score}</span>
          </div>
          <div className="bar" aria-hidden="true">
            <span className={`bar-fill score-${band(s.score)}`} style={{ width: `${s.score}%` }} />
          </div>
          <p className="reason">{s.reason}</p>
          {s.evidence_verified && (
            <blockquote className="evidence">
              <span className="evidence-label">From your resume</span>“{s.evidence}”
            </blockquote>
          )}
        </li>
      ))}
    </ul>
  );
}

function FitTab({ card }) {
  return (
    <div className="fit">
      {!card.meta.job_description_provided && (
        <p className="note">
          No job was given, so you were scored as a <strong>{card.target_role}</strong>. Paste a real posting for a
          sharper comparison.
        </p>
      )}
      <div className="fit-cols">
        <div>
          <h3 className="fit-title good">Strengths</h3>
          <ul className="fit-list">
            {card.strengths.map((s) => (
              <li key={s}>
                <span className="mark good" aria-hidden="true">
                  ✓
                </span>
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="fit-title warn">Gaps for this role</h3>
          <ul className="fit-list">
            {card.gaps.length ? (
              card.gaps.map((g) => (
                <li key={g}>
                  <span className="mark warn" aria-hidden="true">
                    !
                  </span>
                  {g}
                </li>
              ))
            ) : (
              <li className="muted">No major gaps found.</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}

function ImproveTab({ card }) {
  const [copied, setCopied] = useState(-1);
  if (!card.bullet_rewrites.length) {
    return <p className="muted">Your bullets already read well. No rewrites suggested.</p>;
  }
  const copy = async (text, i) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(i);
      setTimeout(() => setCopied(-1), 1500);
    } catch {
      /* clipboard blocked */
    }
  };
  return (
    <div className="rewrites">
      <p className="muted small">Stronger versions of bullets from your resume. They only use facts already in it.</p>
      {card.bullet_rewrites.map((r, i) => (
        <div key={i} className="rewrite">
          <p className="before">
            <span className="tag">Before</span>
            {r.original}
          </p>
          <p className="after">
            <span className="tag tag-after">After</span>
            {r.improved}
          </p>
          <button className="btn btn-ghost btn-sm" onClick={() => copy(r.improved, i)}>
            {copied === i ? "Copied!" : "Copy"}
          </button>
        </div>
      ))}
    </div>
  );
}

function HowItWorks({ card }) {
  const secs = (card.meta.latency_ms / 1000).toFixed(1);
  return (
    <details className="how">
      <summary>How your ratings are calculated</summary>
      <ul>
        <li>The AI scout rates each attribute on the evidence in your resume, ignoring years of experience.</li>
        <li>
          Ratings are then scaled by experience: ×0.80 at 0 years up to ×1.00 at 10+ years. You:{" "}
          <strong>
            {card.years_of_experience} years → ×{card.experience_multiplier.toFixed(2)}
          </strong>
          .
        </li>
        <li>Overall = 25% TEC + 20% PRB + 20% FIT + 15% IMP + 10% COM + 10% ADP.</li>
        <li>Card colour: gold 75+, silver 65–74, bronze below 65. Every stat is between 45 and 99.</li>
        <li>Quotes are shown only if they appear word for word in your resume.</li>
      </ul>
      <p className="muted small">
        Scored by {card.meta.model} in {secs}s. This is a fun, AI-generated estimate, not a hiring decision.
      </p>
    </details>
  );
}
