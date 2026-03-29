import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { UploadCloud } from "lucide-react";
import GlowCard from "../components/UI/GlowCard";
import LoadingSpinner from "../components/UI/LoadingSpinner";
import { uploadPortfolio } from "../services/api";

const Portfolio = () => {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleUpload = async (selectedFile) => {
    if (!selectedFile) return;
    setLoading(true);
    setError("");
    setFile(selectedFile);
    try {
      const data = await uploadPortfolio(selectedFile, "system");
      setResult(data);
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  const xirrGaugeData = useMemo(() => {
    const xirr = Number(result?.xirr_results?.overall_xirr || 0);
    return [
      { name: "XIRR", value: xirr },
      { name: "Remaining", value: Math.max(0, 25 - xirr) },
    ];
  }, [result]);

  const expenseData = useMemo(() => {
    const analysis = result?.expense_analysis || {};
    return [
      { name: "Current", value: Number(analysis.current_expense_ratio || 0) },
      { name: "Optimal", value: Number(analysis.optimal_expense_ratio || 0.6) },
      { name: "Drag", value: Number(analysis.expense_drag_percent || 0) },
    ];
  }, [result]);

  const benchmarkData = useMemo(() => {
    const bm = result?.benchmark_analysis || {};
    const px = Number(result?.xirr_results?.overall_xirr || 0);
    return [
      { name: "Portfolio", value: px },
      { name: "Benchmark", value: Number(bm.benchmark_return || 0) },
    ];
  }, [result]);

  const overlap = result?.overlap_analysis?.overlap_matrix || [];
  const recommendations = result?.rebalancing_plan?.recommendations || [];

  return (
    <div className="space-y-6">
      <GlowCard>
        <div
          className={`rounded-2xl border-2 border-dashed p-10 text-center transition-all ${
            dragging ? "border-[var(--neon-blue)] bg-sky-500/10" : "border-white/20"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleUpload(e.dataTransfer.files?.[0]);
          }}
        >
          <UploadCloud className="mx-auto mb-3 text-[var(--neon-blue)]" size={40} />
          <h3 className="text-lg font-semibold">Drop CAMS PDF or Excel statement</h3>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">or click to browse and upload for instant AI diagnosis</p>
          <input
            type="file"
            className="mt-4"
            accept=".pdf,.xlsx,.csv"
            onChange={(e) => handleUpload(e.target.files?.[0])}
          />
          {file ? <p className="mt-3 text-xs text-slate-300">Selected: {file.name}</p> : null}
        </div>
      </GlowCard>

      {loading ? <LoadingSpinner label="Analyzing portfolio with Portfolio Doctor" /> : null}
      {error ? <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-200">{error}</div> : null}

      {result ? (
        <>
          <section className="grid gap-4 xl:grid-cols-2">
            <GlowCard>
              <h3 className="mb-4 text-lg font-semibold">XIRR Gauge</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={xirrGaugeData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{ background: "#020818", border: "1px solid rgba(0,212,255,0.3)" }} />
                    <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                      {xirrGaugeData.map((entry) => (
                        <Cell key={entry.name} fill={entry.name === "XIRR" ? "#00ff88" : "#1e293b"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </GlowCard>

            <GlowCard>
              <h3 className="mb-4 text-lg font-semibold">Expense Drag</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={expenseData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{ background: "#020818", border: "1px solid rgba(0,212,255,0.3)" }} />
                    <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                      {expenseData.map((entry) => (
                        <Cell key={entry.name} fill={entry.name === "Drag" ? "#ff4444" : "#00d4ff"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </GlowCard>
          </section>

          <section className="grid gap-4 xl:grid-cols-2">
            <GlowCard>
              <h3 className="mb-4 text-lg font-semibold">Overlap Matrix</h3>
              <div className="grid gap-2">
                {overlap.slice(0, 6).map((row, idx) => (
                  <div key={idx} className="rounded-lg border border-white/10 bg-black/20 p-2 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--text-secondary)]">{row.fund_a}</span>
                      <span className="text-[var(--text-secondary)]">{row.fund_b}</span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded bg-white/10">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, Number(row.overlap_percentage || 0))}%` }}
                        className="h-full bg-gradient-to-r from-[var(--neon-blue)] to-[var(--neon-green)]"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </GlowCard>

            <GlowCard>
              <h3 className="mb-4 text-lg font-semibold">Benchmark Comparison</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={benchmarkData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.15)" />
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{ background: "#020818", border: "1px solid rgba(0,212,255,0.3)" }} />
                    <Line type="monotone" dataKey="value" stroke="#00d4ff" strokeWidth={3} dot={{ fill: "#00ff88" }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </GlowCard>
          </section>

          <section>
            <h3 className="mb-3 text-lg font-semibold">AI Recommendations</h3>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {recommendations.slice(0, 6).map((rec, idx) => (
                <GlowCard key={idx}>
                  <p className="text-xs uppercase tracking-[0.12em] text-[var(--text-secondary)]">Action {idx + 1}</p>
                  <p className="mt-2 text-sm text-slate-100">{typeof rec === "string" ? rec : JSON.stringify(rec)}</p>
                </GlowCard>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
};

export default Portfolio;
