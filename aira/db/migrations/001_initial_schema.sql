create extension if not exists "pgcrypto";

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    email text unique not null,
    name text not null,
    risk_profile text not null,
    created_at timestamptz not null default now()
);

create table if not exists portfolios (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    raw_data jsonb not null default '{}'::jsonb,
    xirr float not null default 0,
    created_at timestamptz not null default now()
);

create table if not exists audit_logs (
    id uuid primary key default gen_random_uuid(),
    task_id text not null,
    agent_name text not null,
    user_id text not null,
    input_data jsonb not null default '{}'::jsonb,
    output_data jsonb not null default '{}'::jsonb,
    status text not null,
    confidence_score float not null default 0,
    created_at timestamptz not null default now(),
    completed_at timestamptz null,
    error_message text null
);

create table if not exists market_signals (
    id uuid primary key default gen_random_uuid(),
    symbol text not null,
    signal_type text not null,
    opportunity_score float not null default 0,
    data jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists user_alerts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    signal_id uuid not null references market_signals(id) on delete cascade,
    is_read bool not null default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_portfolios_user_id on portfolios(user_id);
create index if not exists idx_audit_logs_task_id on audit_logs(task_id);
create index if not exists idx_market_signals_symbol on market_signals(symbol);
create index if not exists idx_user_alerts_user_id on user_alerts(user_id);
