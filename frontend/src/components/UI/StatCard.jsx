import { useEffect, useMemo, useState } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import GlowCard from "./GlowCard";

const StatCard = ({ label, value, trend = 0, sublabel = "", tone = "blue" }) => {
  const positive = Number(trend) >= 0;
  const toneGlow = tone === "green" ? "from-emerald-500/20" : tone === "red" ? "from-rose-500/20" : tone === "gold" ? "from-amber-500/20" : "from-sky-500/20";
  const topBorder = tone === "green" ? "bg-emerald-400" : tone === "red" ? "bg-rose-400" : tone === "gold" ? "bg-amber-300" : "bg-sky-400";
  const numericTarget = Number.isFinite(Number(value)) ? Number(value) : null;
  const [displayValue, setDisplayValue] = useState(numericTarget ?? value);

  useEffect(() => {
    if (numericTarget === null) {
      setDisplayValue(value);
      return;
    }
    let raf = 0;
    const duration = 900;
    const started = performance.now();
    const tick = (now) => {
      const progress = Math.min((now - started) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.round(numericTarget * eased));
      if (progress < 1) {
        raf = requestAnimationFrame(tick);
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [numericTarget, value]);

  const renderedValue = useMemo(() => {
    if (numericTarget === null) return value;
    return displayValue;
  }, [displayValue, numericTarget, value]);

  return (
    <GlowCard className="relative overflow-hidden">
      <span className={`absolute left-0 top-0 h-[3px] w-full ${topBorder}`} />
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${toneGlow} to-transparent`} />
      <p className="relative text-xs uppercase tracking-[0.14em] text-[var(--text-secondary)]">{label}</p>
      <h3 className="relative mt-2 animate-counter text-3xl font-semibold text-[var(--text-primary)]">{renderedValue}</h3>
      <div className="relative mt-4 flex items-center justify-between text-xs">
        <span className={`inline-flex items-center gap-1 font-semibold ${positive ? "text-emerald-300" : "text-rose-300"}`}>
          {positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          {Math.abs(Number(trend)).toFixed(1)}%
        </span>
        <span className="text-[var(--text-secondary)]">{sublabel}</span>
      </div>
    </GlowCard>
  );
};

export default StatCard;
