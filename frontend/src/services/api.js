import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
});

const getErrorMessage = (error, fallback) => {
  if (error?.response?.data?.detail) {
    if (typeof error.response.data.detail === "string") return error.response.data.detail;
    return JSON.stringify(error.response.data.detail);
  }
  return error?.message || fallback;
};

const wrap = async (fn, fallback) => {
  try {
    const response = await fn();
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error, fallback));
  }
};

export const getHealth = () => wrap(() => api.get("/health"), "Failed to fetch health status");

export const getSystemStatus = () =>
  wrap(
    async () => {
      try {
        return await api.get("/orchestrate/system-status");
      } catch (error) {
        if (error?.response?.status === 404) {
          const fallback = await api.get("/health");
          return {
            data: {
              checked_at: new Date().toISOString(),
              agents: fallback.data?.agents || [],
              supabase: fallback.data?.supabase || { status: "unknown" },
              last_morning_pipeline_run_at: null,
              total_signals: 0,
              total_conversations: 0,
              system_status: fallback.data?.system_status || "unhealthy",
              execution_time_seconds: 0,
            },
          };
        }
        throw error;
      }
    },
    "Failed to fetch system status",
  );

export const getTopSignals = (limit = 5, minScore = 0, category) =>
  wrap(
    () =>
      api.get("/signals/top", {
        params: {
          limit,
          min_score: minScore,
          category: category || undefined,
        },
      }),
    "Failed to fetch top signals",
  );

export const getFIIDII = () => wrap(() => api.get("/signals/fii-dii"), "Failed to fetch FII/DII data");

export const scanSignals = (force = true) =>
  wrap(() => api.get("/signals/scan", { params: { force } }), "Failed to run signal scan");

export const getPersonalizedSignals = (userId, limit = 10) =>
  wrap(() => api.get(`/signals/${userId}/personalized`, { params: { limit } }), "Failed to fetch personalized signals");

export const analyzeChart = (symbol, includeChart = true) =>
  wrap(
    () =>
      api.get(`/charts/analyze/${encodeURIComponent(symbol)}`, {
        params: { include_chart: includeChart },
      }),
    "Failed to analyze chart",
  );

export const getBreakouts = () => wrap(() => api.get("/charts/breakouts"), "Failed to fetch breakouts");

export const askMarketGPT = (payload) => wrap(() => api.post("/market-gpt/ask", payload), "Failed to fetch MarketGPT response");

export const getMarketSummary = () => wrap(() => api.get("/market-gpt/summary"), "Failed to fetch market summary");

export const analyzeStock = (symbol, userId = "system") =>
  wrap(
    async () => {
      try {
        return await api.get(`/orchestrate/analyze/${encodeURIComponent(symbol)}`, {
          params: { user_id: userId },
        });
      } catch (error) {
        if (error?.response?.status === 404) {
          const ai = await api.get(`/market-gpt/analyze/${encodeURIComponent(symbol)}`, {
            params: { user_id: userId },
          });
          const chart = await api.get(`/charts/analyze/${encodeURIComponent(symbol)}`, {
            params: { include_chart: false },
          });
          return {
            data: {
              symbol,
              technical_analysis: chart.data || {},
              ai_analysis: ai.data?.answer || "AI analysis unavailable",
              combined_signal: (chart.data?.overall_signal || "NEUTRAL").toUpperCase(),
              confidence: Number(chart.data?.confidence || ai.data?.confidence || 0),
            },
          };
        }
        throw error;
      }
    },
    "Failed to fetch stock analysis",
  );

export const getVideoFrames = (userId = "system") =>
  wrap(() => api.get("/video-studio/frames", { params: { user_id: userId } }), "Failed to fetch video frames");

export const getDailyVideo = (includeVideo = false, userId = "system") =>
  wrap(
    () =>
      api.get("/video-studio/daily", {
        params: {
          include_video: includeVideo,
          user_id: userId,
        },
      }),
    "Failed to fetch daily video",
  );

export const uploadPortfolio = (file, userId = "system") => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);
  return wrap(
    () =>
      api.post("/portfolio/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }),
    "Failed to upload portfolio",
  );
};

export const runMorningPipeline = (userId = "system") =>
  wrap(() => api.post("/orchestrate/morning-pipeline", { user_id: userId }), "Failed to run morning pipeline");

export default api;
