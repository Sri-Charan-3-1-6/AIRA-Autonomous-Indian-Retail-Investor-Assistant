const styles = {
  "STRONG BUY": "bg-emerald-500/15 text-emerald-300 border-emerald-400/40",
  BUY: "bg-sky-500/15 text-sky-300 border-sky-400/40",
  WATCH: "bg-amber-500/15 text-amber-300 border-amber-400/40",
  NEUTRAL: "bg-slate-500/20 text-slate-300 border-slate-400/30",
  SELL: "bg-rose-500/15 text-rose-300 border-rose-400/40",
  "STRONG SELL": "bg-red-500/15 text-red-300 border-red-400/40",
};

const Badge = ({ text }) => {
  const key = String(text || "WATCH").toUpperCase();
  const className = styles[key] || styles.WATCH;
  return <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold tracking-wide ${className}`}>{key}</span>;
};

export default Badge;
