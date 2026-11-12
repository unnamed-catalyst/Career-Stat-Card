import { forwardRef } from "react";

const initials = (name = "") =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("") || "?";

const shortName = (name = "") => {
  const parts = name.trim().split(/\s+/);
  return (parts.length > 1 ? parts[parts.length - 1] : parts[0] || "Player").toUpperCase();
};

/** FIFA-style card face. Exported to PNG by CardActions, so keep it self-contained. */
const PlayerCard = forwardRef(function PlayerCard({ card }, ref) {
  const left = card.stats.slice(0, 3);
  const right = card.stats.slice(3);

  return (
    <div ref={ref} className={`card-frame tier-${card.tier}`} role="img" aria-label={`${card.name}: ${card.overall} overall, ${card.target_role}`}>
      <div className="card-inner">
        <div className="card-shine" />
        <div className="card-top">
          <div className="card-rating">
            <span className="ovr">{card.overall}</span>
            <span className="pos">{card.position}</span>
            <span className="rule" />
            <span className="exp" title="Experience band">
              {card.experience_band.replace(" years", "Y")}
            </span>
          </div>
          <div className="avatar" aria-hidden="true">
            <span>{initials(card.name)}</span>
          </div>
        </div>

        <div className="card-name" title={card.name}>
          {shortName(card.name)}
        </div>

        <div className="card-stats">
          <ul>
            {left.map((s) => (
              <li key={s.key}>
                <b>{s.score}</b> {s.code}
              </li>
            ))}
          </ul>
          <span className="vrule" />
          <ul>
            {right.map((s) => (
              <li key={s.key}>
                <b>{s.score}</b> {s.code}
              </li>
            ))}
          </ul>
        </div>

        <div className="card-role">{card.target_role}</div>
        <div className="card-tier-label">{card.tier}</div>
      </div>
    </div>
  );
});

export default PlayerCard;
