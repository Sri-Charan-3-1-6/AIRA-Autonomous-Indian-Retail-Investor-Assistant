"""AIRA module: agents/chart_whisperer/agent.py"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import pandas as pd

from agents.base_agent import BaseAgent
from agents.chart_whisperer import backtester, chart_generator, data_fetcher, indicators, pattern_detector
from db import crud
from models.agent_task import AgentTask

logger = logging.getLogger(__name__)

NIFTY50_SCAN_LIST = [
    "HDFCBANK",
    "RELIANCE",
    "INFY",
    "TCS",
    "ICICIBANK",
    "AXISBANK",
    "KOTAKBANK",
    "SBIN",
    "BAJFINANCE",
    "HINDUNILVR",
    "WIPRO",
    "HCLTECH",
    "MARUTI",
    "TITAN",
    "ASIANPAINT",
    "ULTRACEMCO",
    "NESTLEIND",
    "POWERGRID",
    "NTPC",
    "ONGC",
]


class ChartWhispererAgent(BaseAgent):
    agent_name = "chart_whisperer"
    agent_version = "2.0.0"

    @staticmethod
    def _to_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.set_index("date")
        for col in ["open", "high", "low", "close", "volume", "returns_pct"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna(subset=["open", "high", "low", "close"])

    @staticmethod
    def _indicator_snapshot(df: pd.DataFrame) -> dict[str, Any]:
        if df.empty:
            return {}
        row = df.iloc[-1]
        fields = [
            "rsi_14",
            "macd_line",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "sma_20",
            "sma_50",
            "sma_200",
            "ema_9",
            "ema_21",
            "atr_14",
            "obv",
            "stoch_k",
            "stoch_d",
            "adx_14",
        ]
        snapshot: dict[str, Any] = {}
        for field in fields:
            value = row.get(field)
            snapshot[field] = float(value) if pd.notna(value) else None
        return snapshot

    async def _analyze_symbol(
        self,
        symbol: str,
        period: str,
        interval: str,
        include_chart: bool,
    ) -> dict[str, Any]:
        stock_data = await data_fetcher.fetch_stock_data(symbol, period=period, interval=interval)
        df = self._to_dataframe(stock_data)

        if df.empty:
            raise ValueError(f"No usable OHLCV data for symbol {symbol}")

        df_ind = indicators.calculate_all_indicators(df)
        indicator_interpretation = indicators.interpret_indicators(df_ind)
        patterns_bundle = pattern_detector.detect_all_patterns(df_ind)
        backtest_results = backtester.backtest_multiple_patterns(stock_data["symbol"], df_ind)

        chart_image = None
        if include_chart:
            chart_image = chart_generator.generate_candlestick_chart(
                df_ind,
                stock_data["symbol"],
                patterns_bundle.get("patterns", []),
                {
                    "support_levels": patterns_bundle.get("support_levels", []),
                    "resistance_levels": patterns_bundle.get("resistance_levels", []),
                },
            )

        return {
            "symbol": stock_data["symbol"],
            "company_name": stock_data.get("company_name"),
            "period": period,
            "interval": interval,
            "summary": stock_data.get("summary", {}),
            "indicators": self._indicator_snapshot(df_ind),
            "indicator_interpretation": indicator_interpretation,
            "patterns": patterns_bundle.get("patterns", []),
            "support_levels": patterns_bundle.get("support_levels", []),
            "resistance_levels": patterns_bundle.get("resistance_levels", []),
            "most_significant_pattern": patterns_bundle.get("most_significant_pattern"),
            "pattern_count": patterns_bundle.get("pattern_count", 0),
            "backtest_results": backtest_results,
            "chart_image_base64": chart_image,
            "overall_signal": indicator_interpretation.get("overall_signal", "NEUTRAL"),
            "confidence": float(indicator_interpretation.get("confidence", 0.0)),
            "source": stock_data.get("source", "live"),
        }

    async def _backtest_symbol(self, symbol: str) -> dict[str, Any]:
        stock_data = await data_fetcher.fetch_stock_data(symbol, period="2y", interval="1d")
        df = self._to_dataframe(stock_data)
        if df.empty:
            raise ValueError(f"No historical data available for {symbol}")

        df_ind = indicators.calculate_all_indicators(df)
        results = backtester.backtest_multiple_patterns(stock_data["symbol"], df_ind)
        return {
            "symbol": stock_data["symbol"],
            "period": "2y",
            "total_patterns_tested": len(results),
            "backtest_results": results,
        }

    async def _compare_symbols(self, symbols: list[str], period: str, interval: str) -> dict[str, Any]:
        payloads = await data_fetcher.fetch_multiple_stocks(symbols, period=period)
        comparison: dict[str, Any] = {}

        best_symbol = None
        best_score = -10_000.0

        for request_symbol, payload in payloads.items():
            df = self._to_dataframe(payload)
            if df.empty:
                continue
            df_ind = indicators.calculate_all_indicators(df)
            interpretation = indicators.interpret_indicators(df_ind)
            pattern_count = int(pattern_detector.detect_all_patterns(df_ind).get("pattern_count", 0))

            signal = interpretation.get("overall_signal", "NEUTRAL")
            rank = {
                "STRONG_BUY": 5,
                "BUY": 4,
                "NEUTRAL": 3,
                "SELL": 2,
                "STRONG_SELL": 1,
            }.get(signal, 3)
            confidence = float(interpretation.get("confidence", 0.0))
            composite_score = rank * 20 + confidence * 10 + min(10, pattern_count)

            if composite_score > best_score:
                best_symbol = payload.get("symbol", request_symbol)
                best_score = composite_score

            comparison[payload.get("symbol", request_symbol)] = {
                "company_name": payload.get("company_name"),
                "summary": payload.get("summary", {}),
                "overall_signal": signal,
                "confidence": confidence,
                "trend": interpretation.get("trend"),
                "momentum": interpretation.get("momentum"),
                "pattern_count": pattern_count,
            }

        return {
            "period": period,
            "interval": interval,
            "comparison": comparison,
            "best_opportunity": best_symbol,
        }

    async def _scan_breakouts(self, period: str, interval: str) -> dict[str, Any]:
        started_at = datetime.utcnow()
        payloads = await data_fetcher.fetch_multiple_stocks(NIFTY50_SCAN_LIST, period=period)

        breakout_hits: list[dict[str, Any]] = []
        for request_symbol, payload in payloads.items():
            df = self._to_dataframe(payload)
            if df.empty:
                continue
            df_ind = indicators.calculate_all_indicators(df)

            breakouts = pattern_detector.detect_breakout(df_ind)
            if not breakouts:
                continue

            latest_volume = float(df_ind["volume"].iloc[-1]) if "volume" in df_ind.columns else 0.0
            avg_volume = float(df_ind["volume"].tail(20).mean()) if "volume" in df_ind.columns else 0.0
            volume_surge = (latest_volume / avg_volume * 100.0) if avg_volume > 0 else 0.0

            breakout_hits.append(
                {
                    "symbol": payload.get("symbol", request_symbol),
                    "company_name": payload.get("company_name"),
                    "summary": payload.get("summary", {}),
                    "breakout_patterns": breakouts,
                    "volume_surge": round(volume_surge, 2),
                    "source": payload.get("source", "live"),
                }
            )

        breakout_hits.sort(key=lambda item: float(item.get("volume_surge", 0.0)), reverse=True)
        elapsed = (datetime.utcnow() - started_at).total_seconds()

        return {
            "scan_universe": NIFTY50_SCAN_LIST,
            "breakouts_found": breakout_hits,
            "count": len(breakout_hits),
            "scan_time_seconds": round(elapsed, 3),
        }

    async def run(self, task: AgentTask) -> AgentTask:
        logger.info("ChartWhisperer task started task_id=%s", task.task_id)
        task.status = "running"
        try:
            data = task.input_data or {}
            action = str(data.get("action") or "analyze").lower().strip()
            symbol = str(data.get("symbol") or "").upper().strip()
            symbols = [str(s).upper().strip() for s in data.get("symbols", []) if str(s).strip()]
            period = str(data.get("period") or "6mo")
            interval = str(data.get("interval") or "1d")
            include_chart = bool(data.get("include_chart", True))

            if action == "analyze":
                if not symbol:
                    raise ValueError("symbol is required for analyze action")
                task.output_data = await self._analyze_symbol(symbol, period, interval, include_chart)
                task.confidence_score = 0.86
            elif action == "backtest":
                if not symbol:
                    raise ValueError("symbol is required for backtest action")
                task.output_data = await self._backtest_symbol(symbol)
                task.confidence_score = 0.83
            elif action == "compare":
                if len(symbols) < 2:
                    raise ValueError("symbols list with at least 2 entries is required for compare action")
                task.output_data = await self._compare_symbols(symbols, period, interval)
                task.confidence_score = 0.8
            elif action == "scan_breakouts":
                task.output_data = await self._scan_breakouts(period, interval)
                task.confidence_score = 0.78
            else:
                raise ValueError("action must be one of: analyze, backtest, compare, scan_breakouts")

            task.status = "completed"
            task.completed_at = datetime.utcnow()
            await self.log_to_audit(task, crud)
            logger.info("ChartWhisperer task completed task_id=%s", task.task_id)
            return task
        except Exception as exc:
            logger.exception("ChartWhisperer task failed task_id=%s error=%s", task.task_id, exc)
            task.status = "failed"
            task.error_message = str(exc)
            task.completed_at = datetime.utcnow()
            await self.log_to_audit(task, crud)
            return task

    async def health_check(self) -> dict:
        return {
            "agent": self.agent_name,
            "status": "healthy",
            "version": self.agent_version,
            "phase": "phase_4",
            "capabilities": [
                "technical_indicators",
                "candlestick_pattern_detection",
                "historical_backtesting",
                "chart_image_generation",
                "breakout_scanning",
            ],
        }
