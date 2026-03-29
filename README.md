# AIRA - Autonomous Indian Retail Investor Assistant

## Section 1 — Project title and badges
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)
![Groq](https://img.shields.io/badge/Groq-Llama%203.3%2070B-black)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E)

## Section 2 — One line description
AI-powered multi-agent investment analyst for 14 crore+ Indian retail investors.

## Section 3 — Key Features as a clean list
- 5 Specialized AI Agents
- Real-time NSE Market Signals
- Portfolio Analysis with XIRR Calculation
- AI-powered Conversational Assistant
- Automated Market Summary Videos
- Full Audit Trail

## Section 4 — Architecture
AIRA is orchestrator-first. The orchestrator receives user and scheduled tasks, routes each task to a specialized agent, aggregates outputs, and stores all critical decision artifacts in Supabase and audit logs.

Agent summary:
- Portfolio Doctor: parses portfolio statements and computes analytics, overlap, and XIRR.
- Signal Hunter: monitors market events and scores opportunities.
- Chart Whisperer: performs technical analysis and chart-based backtesting.
- MarketGPT: provides conversational, portfolio-aware market explanations with disclaimers.
- Video Studio: generates daily frame-based market summaries and video-ready artifacts.

Text architecture diagram:

```text
React Dashboard (frontend)
          |
          v
FastAPI API Layer (routers)
          |
          v
Orchestrator --------------------+
   |                             |
   +--> Portfolio Doctor         |
   +--> Signal Hunter            |
   +--> Chart Whisperer          |
   +--> MarketGPT                |
   +--> Video Studio             |
                                 v
                       Supabase PostgreSQL
         (users, portfolios, market_signals, conversations, audit_logs)
```

## Section 5 — Tech Stack table

| Layer | Technology |
|---|---|
| Backend | Python FastAPI |
| AI/LLM | Groq Llama 3.3 70B |
| Database | Supabase PostgreSQL |
| Frontend | React + Tailwind CSS |
| Data Sources | NSE APIs + yfinance + ET Markets |
| Scheduler | APScheduler |

## Section 6 — Quick Start with exact commands

```bash
git clone https://github.com/Sri-Charan-3-1-6/AIRA-Autonomous-Indian-Retail-Investor-Assistant.git
cd AIRA
cp aira/.env.example aira/.env
pip install -r aira/requirements.txt
cd aira
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## Section 7 — Environment Variables table

| Key | Description |
|---|---|
| GROQ_API_KEY | Groq API key used for LLM inference |
| SUPABASE_URL | Supabase project URL |
| SUPABASE_ANON_KEY | Supabase anonymous key |
| SUPABASE_SERVICE_KEY | Supabase service role key for backend writes and privileged queries |
| APP_ENV | Runtime environment (`development` or `production`) |
| APP_VERSION | Application semantic version |

## Section 8 — API Endpoints summary table

| Group | Major Routes |
|---|---|
| Health | `GET /health` |
| User | `POST /user/register`, `GET /user/{user_id}` |
| Orchestrator | `GET /orchestrate/system-status`, `POST /orchestrate/morning-pipeline`, `GET /orchestrate/analyze/{symbol}` |
| Portfolio Doctor | `POST /portfolio/upload`, `GET /portfolio/{user_id}/latest`, `GET /portfolio/{user_id}/history` |
| Signal Hunter | `GET /signals/scan`, `GET /signals/top`, `GET /signals/{user_id}/personalized`, `GET /signals/symbol/{symbol}`, `GET /signals/fii-dii` |
| Chart Whisperer | `GET /charts/analyze/{symbol}`, `GET /charts/breakouts` |
| MarketGPT | `POST /market-gpt/ask`, `POST /market-gpt/scenario`, `GET /market-gpt/summary`, `GET /market-gpt/analyze/{symbol}`, `GET /market-gpt/session/{session_id}/history` |
| Video Studio | `GET /video-studio/daily`, `GET /video-studio/stock/{symbol}`, `GET /video-studio/frames`, `POST /video-studio/trigger` |
| Audit | `GET /audit/logs`, `GET /audit/stats`, `GET /audit/decision/{task_id}`, `GET /audit/compliance-report` |

## Section 9 — Demo credentials or test instructions
- Portfolio Doctor: upload a CAMS PDF or KFintech XLSX to `POST /portfolio/upload`.
- Signal Hunter: run `GET /signals/scan?force=true` and inspect `GET /signals/top`.
- Chart Whisperer: call `GET /charts/analyze/RELIANCE`.
- MarketGPT: call `POST /market-gpt/ask` and verify `sources` and `disclaimer` fields.
- Video Studio: call `GET /video-studio/frames?user_id=system` and verify 6 base64 frames.
- Audit Layer: call `GET /audit/stats` and `GET /audit/compliance-report`.

## Section 10 — Built for ET Hackathon 2026 with team name and acknowledgments
Built for ET Hackathon 2026 by Team AIRA.

Acknowledgments:
- ET Markets data context and market-news reference stream.
- NSE data ecosystem.
- Supabase platform for managed PostgreSQL and API access.
- Groq for low-latency LLM inference.
