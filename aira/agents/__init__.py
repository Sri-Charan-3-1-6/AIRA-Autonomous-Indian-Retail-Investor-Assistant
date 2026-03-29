"""AIRA module: agents/__init__.py"""

from agents.chart_whisperer.agent import ChartWhispererAgent
from agents.market_gpt.agent import MarketGptAgent
from agents.portfolio_doctor.agent import PortfolioDoctorAgent
from agents.signal_hunter.agent import SignalHunterAgent
from agents.video_studio.agent import VideoStudioAgent

__all__ = [
    "PortfolioDoctorAgent",
    "SignalHunterAgent",
    "ChartWhispererAgent",
    "MarketGptAgent",
    "VideoStudioAgent",
]
