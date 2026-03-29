CREATE TABLE IF NOT EXISTS video_outputs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL,
    video_type text NOT NULL,
    script jsonb,
    frames jsonb,
    video_base64 text,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_video_outputs_user_id ON video_outputs(user_id);
CREATE INDEX IF NOT EXISTS idx_video_outputs_created_at ON video_outputs(created_at DESC);
