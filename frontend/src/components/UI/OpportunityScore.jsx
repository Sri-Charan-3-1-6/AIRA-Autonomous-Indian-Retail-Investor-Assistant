import { useEffect, useMemo, useState } from "react";

const OpportunityScore = ({ score = 0, size = 86 }) => {
  const value = Math.max(0, Math.min(100, Number(score) || 0));
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const targetOffset = circumference - (value / 100) * circumference;
  const [offset, setOffset] = useState(circumference);

  useEffect(() => {
    const id = requestAnimationFrame(() => setOffset(targetOffset));
    return () => cancelAnimationFrame(id);
  }, [targetOffset]);

  const tone = useMemo(() => {
    if (value > 60) return "#00ff88";
    if (value >= 40) return "#ffd700";
    return "#ff4444";
  }, [value]);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <span className="absolute inset-0 rounded-full" style={{ boxShadow: `0 0 18px ${tone}55` }} />
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="rgba(148, 163, 184, 0.15)" strokeWidth="7" fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={tone}
          strokeWidth="7"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s ease, stroke 0.35s ease" }}
        />
      </svg>
      <span className="absolute text-lg font-extrabold text-[var(--text-primary)]">{Math.round(value)}</span>
    </div>
  );
};

export default OpportunityScore;
