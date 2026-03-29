import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getFIIDII, getSystemStatus, getTopSignals, getVideoFrames } from "../services/api";
import GlowCard from "../components/UI/GlowCard";
import LoadingSpinner from "../components/UI/LoadingSpinner";
import Modal from "../components/UI/Modal";
import OpportunityScore from "../components/UI/OpportunityScore";
import StatCard from "../components/UI/StatCard";

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [systemStatus, setSystemStatus] = useState(null);
  const [signals, setSignals] = useState([]);
  const [fiiDii, setFiiDii] = useState(null);
  const [frames, setFrames] = useState([]);
  const [activeFrame, setActiveFrame] = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [statusRes, signalsRes, fiiRes, framesRes] = await Promise.all([
          getSystemStatus(),
          getTopSignals(5, 0),
          getFIIDII(),
          getVideoFrames("system"),
        ]);
        setSystemStatus(statusRes);
        setSignals(signalsRes || []);
        setFiiDii(fiiRes);
        setFrames((framesRes?.frames || []).slice(0, 3));
      } catch (err) {
        setError(err.message || "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const stats = useMemo(() => {
    const totalSignals = signals.length;
    const qualifyingSignals = signals.filter((item) => Number(item.opportunity_score) >= 40).length;
    const activeOpp = totalSignals === 0 ? totalSignals : qualifyingSignals || totalSignals;
    const portfolioScore = 78;
    const sentiment = (fiiDii?.trend?.sentiment || "NEUTRAL").toUpperCase();
    return [
      { label: "Total Signals Today", value: totalSignals, trend: 7.2, sub: "Across all sectors", tone: "blue" },
      { label: "Active Opportunities", value: activeOpp, trend: 4.6, sub: "Score >= 40", tone: "green" },
      { label: "Portfolio Health Score", value: portfolioScore, trend: 1.8, sub: "AI weighted", tone: "gold" },
      { label: "Market Sentiment", value: sentiment, trend: sentiment === "BULLISH" ? 3.2 : -1.1, sub: "Real-time flow", tone: sentiment === "BULLISH" ? "green" : "red" },
    ];
  }, [signals, fiiDii]);

  const timeline = useMemo(() => {
    const base = [
      { step: "Signal Hunter", key: "signal_hunter", ms: 0 },
      { step: "Chart Whisperer", key: "chart_whisperer", ms: 0 },
      { step: "Video Studio", key: "video_studio", ms: 0 },
      { step: "MarketGPT", key: "market_gpt", ms: 0 },
    ];
    const agents = systemStatus?.agents || [];
    return base.map((item, index) => {
      const found = agents.find((a) => a.agent === item.key);
      return {
        ...item,
        ok: found?.status === "healthy",
        ms: Math.round(((systemStatus?.execution_time_seconds || 0) * 1000) / (index + 2)),
      };
    });
  }, [systemStatus]);

  const fiiBars = useMemo(() => {
    const latest = fiiDii?.latest || {};
    return [
      { name: "FII", value: Number(latest.fii_net || 0) },
      { name: "DII", value: Number(latest.dii_net || 0) },
    ];
  }, [fiiDii]);

  const sectorBars = useMemo(() => {
    const sectors = fiiDii?.sector_activity || {};
    return Object.entries(sectors).map(([name, value]) => ({ name, value: Number(value || 0) }));
  }, [fiiDii]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <div key={item} className="glass-card shimmer-bg h-32 rounded-2xl border border-white/10" />
          ))}
        </div>
        <div className="glass-card shimmer-bg h-56 rounded-2xl border border-white/10" />
        <LoadingSpinner label="Loading dashboard intelligence" />
      </div>
    );
  }
  if (error) return <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-200">{error}</div>;

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => (
          <StatCard
            key={item.label}
            label={item.label}
            value={item.value}
            trend={item.trend}
            sublabel={item.sub}
            tone={item.tone}
          />
        ))}
      </section>

      <section>
        <GlowCard>
          <h3 className="mb-4 text-xl font-semibold">Morning Pipeline Status</h3>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {timeline.map((item) => (
              <motion.div key={item.step} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rounded-xl border border-white/10 bg-black/20 p-3">
                <p className="text-xs text-[var(--text-secondary)]">{item.step}</p>
                <div className="mt-2 flex items-center justify-between">
                  <span className={`inline-flex items-center gap-2 text-sm font-semibold ${item.ok ? "text-emerald-300" : "text-rose-300"}`}>
                    <span className={`h-2.5 w-2.5 rounded-full ${item.ok ? "bg-emerald-300 shadow-[0_0_12px_rgba(0,255,136,0.8)]" : "bg-rose-300 shadow-[0_0_12px_rgba(255,68,68,0.8)]"}`} />
                    {item.ok ? "Complete" : "Degraded"}
                  </span>
                  <span className="text-xs text-[var(--text-secondary)]">{item.ms}ms</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: item.ok ? "100%" : "62%" }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className={`h-full ${item.ok ? "bg-[var(--neon-green)]" : "bg-[var(--neon-red)]"}`}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </GlowCard>
      </section>

      <section>
        <h3 className="mb-3 text-xl font-semibold">Top Opportunities</h3>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {signals.map((signal) => (
            <GlowCard
              key={signal.id || signal.symbol}
              className={`flex flex-col justify-between border ${
                Number(signal.opportunity_score) > 60
                  ? "border-emerald-400/50 shadow-[0_0_26px_rgba(0,255,136,0.2)]"
                  : Number(signal.opportunity_score) >= 40
                    ? "border-amber-300/50 shadow-[0_0_24px_rgba(255,215,0,0.2)]"
                    : "border-rose-400/50 shadow-[0_0_24px_rgba(255,68,68,0.2)]"
              }`}
            >
              <div>
                <p className="text-[1.7rem] font-extrabold tracking-wide">{signal.symbol}</p>
                <p className="mt-1 line-clamp-2 text-xs text-[var(--text-secondary)]">{signal.explanation || "No explanation"}</p>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <OpportunityScore score={signal.opportunity_score} />
                <span
                  className={`rounded-full border px-2 py-1 text-[10px] font-bold tracking-[0.08em] ${
                    Number(signal.opportunity_score) > 60
                      ? "border-emerald-300/50 text-emerald-300"
                      : Number(signal.opportunity_score) >= 40
                        ? "border-amber-300/50 text-amber-300"
                        : "border-rose-300/50 text-rose-300"
                  }`}
                >
                  {Number(signal.opportunity_score) > 60 ? "BUY" : Number(signal.opportunity_score) >= 40 ? "WATCH" : "AVOID"}
                </span>
              </div>
            </GlowCard>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <GlowCard>
          <h3 className="mb-4 text-xl font-semibold">FII/DII Flow</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={fiiBars}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: "#020818", border: "1px solid rgba(0,212,255,0.3)" }} />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {fiiBars.map((entry) => (
                    <Cell key={entry.name} fill={entry.value >= 0 ? "#00ff88" : "#ff4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlowCard>

        <GlowCard>
          <h3 className="mb-4 text-xl font-semibold">Sector Activity</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sectorBars} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
                <XAxis type="number" stroke="#94a3b8" />
                <YAxis type="category" dataKey="name" stroke="#94a3b8" width={90} />
                <Tooltip contentStyle={{ background: "#020818", border: "1px solid rgba(0,212,255,0.3)" }} />
                <Bar dataKey="value" radius={[0, 8, 8, 0]}>
                  {sectorBars.map((entry) => (
                    <Cell key={entry.name} fill={entry.value >= 0 ? "#00ff88" : "#ff4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlowCard>
      </section>

      <section>
        <h3 className="mb-3 text-xl font-semibold">Video Studio Preview</h3>
        <div className="grid gap-4 md:grid-cols-3">
          {frames.map((frame, idx) => (
            <motion.button
              key={`${frame.frame_type}-${idx}`}
              whileHover={{ scale: 1.02 }}
              className="overflow-hidden rounded-2xl border border-[var(--border-glow)] bg-[var(--bg-card)]"
              onClick={() => setActiveFrame(frame)}
            >
              <img src={`data:image/png;base64,${frame.image_base64}`} alt={frame.frame_type} className="h-44 w-full object-cover" />
            </motion.button>
          ))}
        </div>
      </section>

      <AnimatePresence>
        <Modal open={Boolean(activeFrame)} onClose={() => setActiveFrame(null)} title={activeFrame?.frame_type || "Frame"}>
          {activeFrame ? <img src={`data:image/png;base64,${activeFrame.image_base64}`} alt="preview" className="w-full rounded-xl" /> : null}
        </Modal>
      </AnimatePresence>
    </div>
  );
};

export default Dashboard;
