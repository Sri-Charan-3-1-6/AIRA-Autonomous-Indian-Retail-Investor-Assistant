"""AIRA module: orchestrator/agent_registry.py"""

from agents.chart_whisperer.agent import ChartWhispererAgent
from agents.market_gpt.agent import MarketGptAgent
from agents.portfolio_doctor.agent import PortfolioDoctorAgent
from agents.signal_hunter.agent import SignalHunterAgent
from agents.video_studio.agent import VideoStudioAgent


def build_agent_registry() -> dict:
    return {
        "portfolio_doctor": PortfolioDoctorAgent(),
        "signal_hunter": SignalHunterAgent(),
        "chart_whisperer": ChartWhispererAgent(),
        "market_gpt": MarketGptAgent(),
        "video_studio": VideoStudioAgent(),
    }


def register_all_agents(orchestrator) -> None:
    for name, agent in build_agent_registry().items():
        orchestrator.register_agent(name, agent)
