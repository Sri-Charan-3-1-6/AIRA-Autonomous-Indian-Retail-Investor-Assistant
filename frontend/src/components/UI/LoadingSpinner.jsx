const LoadingSpinner = ({ label = "Loading AIRA" }) => (
  <div className="flex min-h-[200px] flex-col items-center justify-center gap-4 text-slate-300">
    <div className="relative h-16 w-16">
      <div className="absolute inset-0 rounded-full border-2 border-cyan-500/20" />
      <div className="absolute inset-0 animate-spin rounded-full border-[3px] border-transparent border-t-[var(--neon-blue)] border-r-[var(--neon-blue)] shadow-[0_0_20px_rgba(0,212,255,0.55)]" />
      <div className="absolute inset-[11px] animate-pulse rounded-full border border-cyan-300/60 shadow-[0_0_14px_rgba(0,212,255,0.45)]" />
    </div>
    <p className="text-sm tracking-[0.16em] text-[var(--text-secondary)]">{label}</p>
  </div>
);

export default LoadingSpinner;
