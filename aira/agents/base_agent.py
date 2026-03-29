"""AIRA module: agents/base_agent.py"""

from abc import ABC, abstractmethod

from models.agent_task import AgentTask


class BaseAgent(ABC):
    agent_name: str = "base_agent"
    agent_version: str = "1.0.0"

    @abstractmethod
    async def run(self, task: AgentTask) -> AgentTask:
        raise NotImplementedError

    async def health_check(self) -> dict:
        return {
            "agent": self.agent_name,
            "status": "healthy",
            "version": self.agent_version,
        }

    async def log_to_audit(self, task: AgentTask, db) -> None:
        await db.log_audit(task)
