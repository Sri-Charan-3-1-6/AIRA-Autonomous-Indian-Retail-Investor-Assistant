import { useEffect, useMemo, useState } from "react";
import GlowCard from "../components/UI/GlowCard";
import LoadingSpinner from "../components/UI/LoadingSpinner";
import { getDailyVideo } from "../services/api";

const sectionKeys = ["intro", "market_overview", "top_opportunities", "sector_watch", "closing"];

const Video = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [frameIndex, setFrameIndex] = useState(0);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getDailyVideo(false, "system");
      setData(response);
      setFrameIndex(0);
    } catch (err) {
      setError(err.message || "Failed to load video data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!data?.frames?.length) return;
    const timer = setInterval(() => {
      setFrameIndex((prev) => (prev + 1) % data.frames.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [data]);

  const currentFrame = useMemo(() => data?.frames?.[frameIndex], [data, frameIndex]);

  const downloadVideo = () => {
    if (!data?.video_base64) return;
    const link = document.createElement("a");
    link.href = `data:video/mp4;base64,${data.video_base64}`;
    link.download = "aira-market-video.mp4";
    link.click();
  };

  if (loading) return <LoadingSpinner label="Loading Video Studio" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={load} className="rounded-xl border border-[var(--neon-blue)]/40 bg-sky-500/20 px-4 py-2 text-sm font-semibold text-sky-200">
          Generate Latest Frames
        </button>
        <div className="text-sm text-[var(--text-secondary)]">
          Frame {Math.min(frameIndex + 1, data?.frames?.length || 0)} / {data?.frames?.length || 0}
        </div>
        <button
          onClick={downloadVideo}
          disabled={!data?.video_base64}
          className="rounded-xl border border-emerald-400/40 bg-emerald-500/20 px-4 py-2 text-sm font-semibold text-emerald-200 disabled:opacity-40"
        >
          Download Video
        </button>
      </div>

      {error ? <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-200">{error}</div> : null}

      <GlowCard className="overflow-hidden">
        {currentFrame?.image_base64 ? (
          <img
            src={`data:image/png;base64,${currentFrame.image_base64}`}
            alt={currentFrame.frame_type}
            className="h-[420px] w-full object-cover transition-opacity duration-700"
          />
        ) : (
          <div className="flex h-[420px] items-center justify-center text-[var(--text-secondary)]">No frames available</div>
        )}
      </GlowCard>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sectionKeys.map((key) => (
          <GlowCard key={key} className="md:min-h-[150px]">
            <p className="text-xs uppercase tracking-[0.12em] text-[var(--text-secondary)]">{key.replace(/_/g, " ")}</p>
            <p className="mt-3 text-sm text-slate-100">{data?.script?.[key] || "No content"}</p>
          </GlowCard>
        ))}
      </section>
    </div>
  );
};

export default Video;
