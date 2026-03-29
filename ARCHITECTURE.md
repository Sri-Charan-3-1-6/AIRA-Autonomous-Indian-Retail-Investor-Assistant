# AIRA Architecture

## Overview
AIRA is a multi-agent, orchestrator-driven AI system designed for Indian retail-investing workflows. A FastAPI backend coordinates specialized agents, persists outputs to Supabase, and serves both frontend dashboards and API clients with traceable, auditable decisions.

## Agent Descriptions

| Agent | Role | Key Capabilities |
|---|---|---|
| Portfolio Doctor | Portfolio diagnostics and recommendations | CAMS PDF parsing, KFintech Excel parsing, XIRR, overlap detection, expense analysis, benchmark comparison, tax analysis, AI recommendations |
| Signal Hunter | Real-time signal intelligence | NSE filings monitoring, insider trade detection, bulk deal tracking, FII/DII flow analysis, personalized filtering, opportunity scoring |
| Chart Whisperer | Technical analysis engine | Indicators, candlestick patterns, support/resistance, backtesting, breakout scanning, chart image generation |
| MarketGPT | Conversational investment analyst | Portfolio-aware chat, scenario simulation, RAG context composition, multi-turn memory, stock analysis, daily market summary |
| Video Studio | Automated market video summaries | Script generation, chart frame rendering, frames-only mode, MP4 generation pipeline |

## Communication Flow
1. Frontend or client calls FastAPI route.
2. Route invokes orchestrator or dedicated agent route.
3. Orchestrator dispatches task to a registered agent.
4. Agent fetches data/tool outputs and computes decision payload.
5. Results are persisted to Supabase where needed.
6. Audit record is stored in `audit_logs` for traceability.
7. Response is returned to client with confidence and metadata.

## Tool Integrations
- Supabase PostgreSQL for users, portfolios, signals, conversations, audit logs.
- Groq Llama 3.3 70B for conversational and analysis generation.
- NSE/public market feeds and ET Markets extraction.
- yfinance for additional market/price context.
- APScheduler for timed scans and recurring workflows.
- Matplotlib/mplfinance for chart and frame rendering.

## Error Handling
- Per-agent exception handling with task status transitions to failed.
- Structured API error responses with HTTP 4xx/5xx semantics.
- Health and system status endpoints for runtime observability.
- Graceful fallback behavior in frontend API layer for missing optional routes.

## Audit Trail
- Every agent task can be written into `audit_logs` with task_id, input_data, output_data, status, confidence_score, created_at, completed_at, and error_message.
- Compliance endpoints provide aggregate visibility (`/audit/stats`) and per-task decision trace (`/audit/decision/{task_id}`).
- Compliance report endpoint verifies confidence distribution and MarketGPT disclaimer coverage.

## Tech Stack
- Backend: Python 3.11+ FastAPI
- Frontend: React + Tailwind CSS
- Data: Supabase PostgreSQL
- LLM: Groq Llama 3.3 70B
- Scheduling: APScheduler
- Visualization: Recharts, Matplotlib, mplfinance

## Performance Metrics
Measured during final integration verification:
- Morning pipeline: under 60 seconds
- Chart analysis: 10.8 seconds
- Signal scan output: 124 signals
- Video generation (frames mode): 6 frames in under 10 seconds
