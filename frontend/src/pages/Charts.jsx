import { useState } from "react";
import GlowCard from "../components/UI/GlowCard";
import LoadingSpinner from "../components/UI/LoadingSpinner";
import Badge from "../components/UI/Badge";
import { analyzeChart } from "../services/api";

const Charts = () => {
  const [symbol, setSymbol] = useState("INFY");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await analyzeChart(symbol, true);
      setData(response);
    } catch (err) {
      setError(err.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const imageSrc = data?.chart_image_base64
    ? data.chart_image_base64.startsWith("data:image")
      ? data.chart_image_base64
      : `data:image/png;base64,${data.chart_image_base64}`
    : null;

  return (
    <div className="space-y-6">
      <GlowCard className="flex flex-wrap items-center gap-3">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="Enter NSE symbol (INFY)"
          className="min-w-[240px] flex-1 rounded-xl border border-white/15 bg-black/20 px-4 py-2 text-sm outline-none focus:border-[var(--neon-blue)]"
        />
        <button onClick={runAnalysis} className="rounded-xl border border-[var(--neon-blue)]/40 bg-sky-500/20 px-4 py-2 text-sm font-semibold text-sky-200">
          Analyze
        </button>
      </GlowCard>

      {loading ? <LoadingSpinner label="Analyzing chart" /> : null}
      {error ? <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-200">{error}</div> : null}

      {data ? (
        <>
          <GlowCard>
            <h3 className="mb-3 text-lg font-semibold">{data.symbol} Technical Chart</h3>
            {imageSrc ? <img src={imageSrc} alt={data.symbol} className="w-full rounded-xl border border-white/10" /> : <p>No chart image available.</p>}
          </GlowCard>

          <div className="grid gap-4 md:grid-cols-3">
            <GlowCard>
              <p className="text-xs text-[var(--text-secondary)]">RSI</p>
              <p className="mt-1 text-2xl font-semibold">{Number(data.indicators?.rsi_14 || 0).toFixed(2)}</p>
            </GlowCard>
            <GlowCard>
              <p className="text-xs text-[var(--text-secondary)]">MACD</p>
              <p className="mt-1 text-2xl font-semibold">{Number(data.indicators?.macd_line || 0).toFixed(2)}</p>
            </GlowCard>
            <GlowCard>
              <p className="text-xs text-[var(--text-secondary)]">Trend</p>
              <p className="mt-1 text-2xl font-semibold">{data.indicator_interpretation?.trend || "NA"}</p>
            </GlowCard>
          </div>

          <GlowCard>
            <h3 className="mb-3 text-lg font-semibold">Detected Patterns</h3>
            <div className="flex flex-wrap gap-2">
              {(data.patterns || []).slice(0, 10).map((pattern, idx) => (
                <Badge key={idx} text={pattern.pattern_name || pattern.type || "WATCH"} />
              ))}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div>
                <p className="mb-1 text-xs text-[var(--text-secondary)]">Support</p>
                <p className="text-sm text-slate-200">{(data.support_levels || []).join(", ") || "NA"}</p>
              </div>
              <div>
                <p className="mb-1 text-xs text-[var(--text-secondary)]">Resistance</p>
                <p className="text-sm text-slate-200">{(data.resistance_levels || []).join(", ") || "NA"}</p>
              </div>
            </div>
          </GlowCard>

          <GlowCard>
            <h3 className="mb-3 text-lg font-semibold">Backtest Results</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-[var(--text-secondary)]">
                    <th className="py-2 pr-3">Pattern</th>
                    <th className="py-2 pr-3">Trades</th>
                    <th className="py-2 pr-3">Success Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.backtest_results || []).map((row, idx) => {
                    const rate = Number(row.success_rate || 0);
                    return (
                      <tr key={idx} className="border-b border-white/5">
                        <td className="py-2 pr-3">{row.pattern_name || "Pattern"}</td>
                        <td className="py-2 pr-3">{row.total_trades ?? "-"}</td>
                        <td className={`py-2 pr-3 font-semibold ${rate >= 50 ? "text-emerald-300" : "text-rose-300"}`}>{rate.toFixed(1)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </GlowCard>
        </>
      ) : null}
    </div>
  );
};

export default Charts;
