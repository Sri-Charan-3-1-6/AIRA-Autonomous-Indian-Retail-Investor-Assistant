import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import Badge from "../components/UI/Badge";
import GlowCard from "../components/UI/GlowCard";
import LoadingSpinner from "../components/UI/LoadingSpinner";
import Modal from "../components/UI/Modal";
import { getTopSignals, scanSignals } from "../services/api";

const filters = ["ALL", "STRONG BUY", "BUY", "WATCH"];

const Signals = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);
  const [signals, setSignals] = useState([]);
  const [activeFilter, setActiveFilter] = useState("ALL");
  const [selected, setSelected] = useState(null);

  const loadSignals = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getTopSignals(20, 0);
      setSignals(data || []);
    } catch (err) {
      setError(err.message || "Failed to fetch signals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSignals();
  }, []);

  const filtered = useMemo(() => {
    if (activeFilter === "ALL") return signals;
    return signals.filter((signal) => String(signal.category || "").toUpperCase() === activeFilter);
  }, [activeFilter, signals]);

  const onScan = async () => {
    setScanning(true);
    setError("");
    try {
      await scanSignals(true);
      await loadSignals();
    } catch (err) {
      setError(err.message || "Scan failed");
    } finally {
      setScanning(false);
    }
  };

  if (loading) return <LoadingSpinner label="Loading signals" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          {filters.map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold tracking-wide ${
                activeFilter === filter
                  ? "border-[var(--neon-blue)] bg-sky-500/20 text-sky-200"
                  : "border-white/15 bg-white/5 text-slate-300"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
        <button
          onClick={onScan}
          disabled={scanning}
          className="rounded-xl border border-[var(--neon-green)]/40 bg-emerald-500/20 px-4 py-2 text-sm font-semibold text-emerald-200 disabled:opacity-50"
        >
          {scanning ? "Scanning..." : "Run Live Scan"}
        </button>
      </div>

      {error ? <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-200">{error}</div> : null}

      <motion.div layout className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <AnimatePresence>
          {filtered.map((signal, index) => (
            <motion.div
              key={`${signal.id || signal.symbol}-${index}`}
              initial={{ opacity: 0, y: 22 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ delay: index * 0.03 }}
            >
              <GlowCard className="cursor-pointer" onClick={() => setSelected(signal)}>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-bold tracking-wide">{signal.symbol}</h3>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">{signal.company}</p>
                  </div>
                  <Badge text={signal.category} />
                </div>
                <p className="mt-4 text-3xl font-semibold text-[var(--neon-blue)]">{Math.round(signal.opportunity_score || 0)}</p>
                <p className="mt-2 line-clamp-3 text-sm text-slate-300">{signal.explanation || "No explanation"}</p>
              </GlowCard>
            </motion.div>
          ))}
        </AnimatePresence>
      </motion.div>

      <Modal open={Boolean(selected)} onClose={() => setSelected(null)} title={selected?.symbol || "Signal Detail"}>
        {selected ? <pre className="overflow-auto rounded-xl bg-black/30 p-4 text-xs text-slate-200">{JSON.stringify(selected, null, 2)}</pre> : null}
      </Modal>
    </div>
  );
};

export default Signals;
