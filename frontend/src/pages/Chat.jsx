import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { SendHorizontal, User } from "lucide-react";
import GlowCard from "../components/UI/GlowCard";
import LoadingSpinner from "../components/UI/LoadingSpinner";
import Badge from "../components/UI/Badge";
import { askMarketGPT } from "../services/api";

const suggested = [
  "What is current market sentiment?",
  "Analyze HDFC Bank",
  "What if IT sector drops 5%?",
  "Summarize today's market",
];

const renderRichText = (text) => {
  const lines = String(text || "").split("\n");
  return lines.map((line, idx) => {
    if (line.startsWith("- ")) return <li key={idx}>{line.slice(2)}</li>;
    const bolded = line.replace(/\*\*(.*?)\*\*/g, "$1");
    return <p key={idx}>{bolded || "\u00A0"}</p>;
  });
};

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState("");

  const send = async (question) => {
    if (!question?.trim()) return;
    setError("");
    const userMessage = { role: "user", content: question, sources: [] };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await askMarketGPT({
        user_id: "system",
        question,
        session_id: sessionId || null,
        include_portfolio_context: true,
      });

      if (response.session_id && !sessionId) setSessionId(response.session_id);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          sources: response.sources || [],
        },
      ]);
    } catch (err) {
      setError(err.message || "Chat failed");
    } finally {
      setLoading(false);
    }
  };

  const hasMessages = useMemo(() => messages.length > 0, [messages]);

  return (
    <div className="flex h-[calc(100vh-130px)] flex-col gap-4">
      <GlowCard className="py-3">
        <p className="text-xs text-[var(--text-secondary)]">
          Disclaimer: This analysis is for informational purposes only and does not constitute financial advice.
        </p>
      </GlowCard>

      <GlowCard className="flex-1 overflow-y-auto">
        {!hasMessages && !loading ? (
          <div className="flex h-full items-center justify-center text-sm text-[var(--text-secondary)]">Start a conversation with MarketGPT Pro.</div>
        ) : null}

        <div className="space-y-4">
          {messages.map((message, idx) => (
            <motion.div key={idx} initial={{ opacity: 0, x: message.role === "user" ? 20 : -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.25, ease: "easeOut" }} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl border p-4 backdrop-blur-xl ${message.role === "user" ? "border-cyan-400/30 bg-cyan-500/12" : "border-white/10 bg-white/5"}`}>
                <div className="mb-2 flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                  {message.role === "user" ? (
                    <User size={14} />
                  ) : (
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-[10px] font-bold text-cyan-200 shadow-[0_0_16px_rgba(0,212,255,0.55)]">
                      AI
                    </span>
                  )}
                  {message.role === "user" ? "You" : "AIRA"}
                </div>
                <div className="space-y-1 text-sm text-slate-100">{renderRichText(message.content)}</div>
                {message.sources?.length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {message.sources.map((source, sourceIdx) => (
                      <Badge key={sourceIdx} text={source} />
                    ))}
                  </div>
                ) : null}
              </div>
            </motion.div>
          ))}

          {loading ? (
            <div className="flex justify-start">
              <div className="inline-flex items-center gap-3 rounded-2xl border border-cyan-400/25 bg-white/5 px-4 py-3 backdrop-blur-xl">
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-[10px] font-bold text-cyan-200 shadow-[0_0_16px_rgba(0,212,255,0.55)]">AI</span>
                <span className="flex items-center gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-300 [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-300 [animation-delay:120ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-cyan-300 [animation-delay:240ms]" />
                </span>
              </div>
            </div>
          ) : null}
        </div>
      </GlowCard>

      <div className="flex flex-wrap gap-2">
        {suggested.map((q) => (
          <button key={q} onClick={() => send(q)} className="rounded-full border border-white/15 px-3 py-1 text-xs text-slate-300 hover:border-[var(--neon-blue)]">
            {q}
          </button>
        ))}
      </div>

      {error ? <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</div> : null}

      <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[var(--bg-card)] p-3 focus-within:border-cyan-300/60 focus-within:shadow-[0_0_24px_rgba(0,212,255,0.3)]">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send(input);
          }}
          placeholder="Ask MarketGPT Pro..."
          className="flex-1 bg-transparent text-sm outline-none"
        />
        <button onClick={() => send(input)} disabled={loading} className="rounded-xl bg-[var(--neon-blue)]/20 p-2 text-[var(--neon-blue)] shadow-[0_0_14px_rgba(0,212,255,0.32)] disabled:opacity-60">
          <SendHorizontal size={18} />
        </button>
      </div>
    </div>
  );
};

export default Chat;
