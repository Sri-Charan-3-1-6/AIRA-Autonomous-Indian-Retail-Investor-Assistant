CREATE TABLE IF NOT EXISTS daily_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text,
    signals_found int,
    breakouts_found int,
    video_frames int,
    market_summary text,
    top_opportunities jsonb,
    execution_time_seconds float,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_daily_reports_created_at ON daily_reports(created_at DESC);
