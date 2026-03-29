import { motion } from "framer-motion";
import { Bot, CandlestickChart, ChartNoAxesCombined, Clapperboard, LayoutDashboard, ShieldCheck, Signal, Wallet } from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/portfolio", label: "Portfolio Doctor", icon: Wallet },
  { to: "/signals", label: "Signal Hunter", icon: Signal },
  { to: "/charts", label: "Chart Whisperer", icon: CandlestickChart },
  { to: "/chat", label: "MarketGPT", icon: Bot },
  { to: "/video", label: "Video Studio", icon: Clapperboard },
];

const Sidebar = () => {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-16 w-full items-center border-b border-white/10 bg-[var(--bg-secondary)]/90 px-4 backdrop-blur-xl md:h-screen md:w-[240px] md:flex-col md:items-stretch md:border-b-0 md:border-r md:px-5 md:py-5">
      <motion.div
        className="mr-4 flex items-center gap-3 md:mb-10 md:mr-0"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border-glow)] bg-[var(--bg-primary)] shadow-[0_0_28px_rgba(0,212,255,0.28)]">
          <ChartNoAxesCombined size={26} className="text-[var(--neon-blue)]" />
          <span className="absolute inset-0 rounded-2xl animate-pulse-glow" />
        </div>
        <div>
          <p className="text-xs tracking-[0.16em] text-[var(--text-secondary)]">AIRA CORE</p>
          <h1 className="text-xl font-bold text-[var(--text-primary)] [text-shadow:0_0_14px_rgba(0,212,255,0.42)]">Autonomous Indian Retail Investor Assistant</h1>
        </div>
      </motion.div>

      <nav className="flex flex-1 items-center gap-2 overflow-x-auto md:block md:space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.to} to={item.to} end={item.to === "/"}>
              {({ isActive }) => (
                <motion.div
                  whileHover={{ x: 6 }}
                  className={`group relative flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-all ${
                    isActive
                      ? "active-pulse-border border-cyan-300/40 bg-gradient-to-r from-cyan-500/25 via-sky-500/20 to-transparent text-[var(--text-primary)] shadow-[inset_3px_0_0_var(--neon-blue)]"
                      : "border-transparent text-[var(--text-secondary)] hover:border-white/10 hover:bg-cyan-400/10 hover:shadow-[0_0_16px_rgba(0,212,255,0.18)]"
                  }`}
                >
                  {isActive ? <span className="absolute left-0 top-1/2 h-8 w-[3px] -translate-y-1/2 rounded-r-full bg-[var(--neon-blue)] shadow-[0_0_14px_rgba(0,212,255,0.85)]" /> : null}
                  <Icon size={18} className={isActive ? "text-[var(--neon-blue)]" : "text-slate-400 group-hover:text-slate-200"} />
                  <span className="text-sm font-medium">{item.label}</span>
                </motion.div>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="hidden rounded-xl border border-emerald-400/30 bg-emerald-500/10 p-3 md:block">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(0,255,136,0.85)]" />
          <ShieldCheck size={14} className="text-emerald-300" />
          <p className="text-xs font-semibold text-emerald-300">All Systems Live</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
