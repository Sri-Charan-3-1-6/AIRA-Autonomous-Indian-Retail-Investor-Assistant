import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

const titleMap = {
  "/": "Unified Intelligence Dashboard",
  "/portfolio": "Portfolio Doctor",
  "/signals": "Signal Hunter",
  "/charts": "Chart Whisperer",
  "/chat": "MarketGPT Pro",
  "/video": "Video Studio",
};

const tickerData = [
  { label: "NIFTY 50", value: "22,487.30", change: +0.74 },
  { label: "SENSEX", value: "73,228.12", change: -0.18 },
];

const Header = () => {
  const location = useLocation();
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const title = useMemo(() => titleMap[location.pathname] || "AIRA", [location.pathname]);

  return (
    <header className="sticky top-16 z-30 border-b border-white/10 bg-[var(--bg-secondary)]/40 backdrop-blur-xl md:top-0 md:ml-[240px]">
      <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-[var(--neon-blue)]/90 to-transparent" />
      <div className="flex min-h-20 items-center justify-between px-6">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">{title}</h2>
          <p className="text-xs text-[var(--text-secondary)]">{now.toLocaleString()}</p>
        </div>

        <div className="hidden items-center gap-3 xl:flex">
          {tickerData.map((ticker) => (
            <div key={ticker.label} className="rounded-xl border border-white/10 bg-[var(--bg-card)] px-3 py-2 text-xs shadow-[0_0_16px_rgba(0,212,255,0.12)]">
              <p className="text-[11px] font-semibold tracking-[0.12em] text-[var(--text-secondary)]">{ticker.label}</p>
              <div className="flex items-center gap-2">
                <span className="relative text-base font-bold text-[var(--text-primary)]">
                  {ticker.value}
                  <span className="absolute -bottom-1 left-0 h-[2px] w-full origin-left animate-pulse bg-gradient-to-r from-transparent via-[var(--neon-blue)] to-transparent" />
                </span>
                <span className={`font-semibold ${ticker.change >= 0 ? "text-emerald-300 [text-shadow:0_0_10px_rgba(0,255,136,0.8)]" : "text-rose-300 [text-shadow:0_0_10px_rgba(255,68,68,0.85)]"}`}>
                  {ticker.change >= 0 ? "+" : ""}
                  {ticker.change.toFixed(2)}%
                </span>
              </div>
            </div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          className="inline-flex items-center gap-2 rounded-full border border-[var(--border-glow)] bg-sky-500/10 px-4 py-2 text-xs text-[var(--text-primary)]"
        >
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[var(--neon-green)]" />
          AIRA v1.0
        </motion.div>
      </div>
    </header>
  );
};

export default Header;
