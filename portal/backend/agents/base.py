"""
Base class for every agent.

An agent does one job (execute), records what it is doing step by step so
the portal can show its activity live, and saves its result as a report.
"""
import asyncio
import logging
import time
from abc import ABC, abstractmethod

MAX_LOG_LINES = 50


class Agent(ABC):
    name = "agent"      # report file name and API path
    title = "Agent"     # shown in the portal

    def __init__(self, store):
        self.store = store
        self.log = logging.getLogger(f"agent.{self.name}")
        self._lock = asyncio.Lock()
        self.running = False
        self.steps = []
        self.run_count = 0
        self.last_error = None

    def step(self, message):
        """Record one line of activity."""
        self.steps.append({"t": time.time(), "message": message})
        self.steps = self.steps[-MAX_LOG_LINES:]
        self.log.info(message)

    async def run(self):
        """Run the agent once and save its report. Concurrent calls wait their turn."""
        async with self._lock:
            self.running = True
            self.steps = []
            self.last_error = None
            started = time.time()
            self.step(f"{self.title} started")
            try:
                report = await self.execute()
            except Exception as e:
                self.last_error = str(e)
                self.step(f"Failed: {e}")
                self.log.exception("%s failed", self.title)
                raise
            finally:
                self.running = False
            self.run_count += 1
            report.update({
                "agent": self.name,
                "run": self.run_count,
                "started_at": started,
                "finished_at": time.time(),
            })
            self.store.save(self.name, report)
            self.step(f"Report saved ({time.time() - started:.1f}s)")
            return report

    async def run_every(self, seconds):
        """Background loop used by the API server."""
        while True:
            try:
                await self.run()
            except Exception:
                pass  # already logged; try again next round
            await asyncio.sleep(seconds)

    def status(self):
        report = self.store.load(self.name) or {}
        return {
            "name": self.name,
            "title": self.title,
            "running": self.running,
            "run_count": report.get("run", self.run_count),
            "last_run": report.get("finished_at"),
            "last_error": self.last_error,
            "steps": self.steps,
        }

    @abstractmethod
    async def execute(self) -> dict:
        """Do the agent's work and return its report."""
