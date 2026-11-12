import { useState } from "react";
import { toPng } from "html-to-image";

export default function CardActions({ card, cardRef, onReset }) {
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const download = async () => {
    if (!cardRef.current) return;
    setBusy(true);
    try {
      const url = await toPng(cardRef.current, { pixelRatio: 3, cacheBust: true });
      const a = document.createElement("a");
      a.href = url;
      a.download = `${card.name.replace(/[^\w-]+/g, "-").toLowerCase()}-career-card.png`;
      a.click();
    } catch (err) {
      console.error("PNG export failed", err);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    const tier = card.tier[0].toUpperCase() + card.tier.slice(1);
    const stats = card.stats.map((s) => `${s.code} ${s.score}`).join(" · ");
    const text = `${card.name}: ${card.overall} OVR ${tier} · ${card.target_role}\n${stats}\nMade with Career Stat Card`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked */
    }
  };

  return (
    <div className="card-actions">
      <button className="btn btn-primary" onClick={download} disabled={busy}>
        {busy ? "Saving…" : "Download card"}
      </button>
      <button className="btn btn-ghost" onClick={copy}>
        {copied ? "Copied!" : "Copy stats"}
      </button>
      <button className="btn btn-link" onClick={onReset}>
        Score another resume
      </button>
    </div>
  );
}
