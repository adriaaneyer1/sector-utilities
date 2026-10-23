"""
DeltaStream portal API.

The pages show whatever the agents last reported:
  GET  /api/devices              Discovery Agent report + compliance verdict (Devices page)
  GET  /api/filters              sector / location / company options from sites.json
  GET  /api/compliance           Compliance Agent report (Compliance page)
  GET  /api/agents               status and live activity of both agents
  POST /api/agents/{name}/run    run an agent now ("discovery" or "compliance")

If frontend/dist exists (after `npm run build`), it is served at / so the
whole portal can be deployed as one service.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from agents.compliance_agent import ComplianceAgent
from agents.discovery_agent import DiscoveryAgent
from agents.store import ReportStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

store = ReportStore(config.REPORTS_DIR)
discovery = DiscoveryAgent(store)
compliance = ComplianceAgent(store)
AGENTS = {a.name: a for a in (discovery, compliance)}


async def _startup_runs():
    """Fresh reports on start: discover first, then check compliance."""
    try:
        await discovery.run()
        await compliance.run()
    except Exception:
        pass  # logged by the agent; the scheduled runs will retry


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(_startup_runs())]
    if config.DISCOVERY_INTERVAL > 0:
        tasks.append(asyncio.create_task(_after(discovery.run_every(config.DISCOVERY_INTERVAL), config.DISCOVERY_INTERVAL)))
    if config.COMPLIANCE_INTERVAL > 0:
        tasks.append(asyncio.create_task(_after(compliance.run_every(config.COMPLIANCE_INTERVAL), config.COMPLIANCE_INTERVAL)))
    yield
    for t in tasks:
        t.cancel()


async def _after(coro, delay):
    await asyncio.sleep(delay)
    await coro


app = FastAPI(title="DeltaStream Portal API", lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/devices")
def devices():
    """Discovery report, with each device's latest compliance verdict added."""
    report = store.load("discovery") or {"devices": [], "summary": None, "finished_at": None}
    checked = {d["id"]: d for d in (store.load("compliance") or {}).get("devices", [])}
    labels = {"pass": "Compliant", "fail": "Non-Compliant"}
    for d in report["devices"]:
        verdict = checked.get(d["id"], {})
        d["compliance"] = labels.get(verdict.get("result"), "Not assessed")
        d["violations"] = verdict.get("violations", [])
    return report


@app.get("/api/filters")
def filters():
    """Dropdown options for the global search, taken from the provisioned sites."""
    sites = config.load_sites()
    return {key: sorted({s[field] for s in sites})
            for key, field in (("sectors", "sector"), ("locations", "location"), ("companies", "company"))}


@app.get("/api/compliance")
def compliance_report():
    return store.load("compliance") or {"devices": [], "summary": None, "finished_at": None}


@app.get("/api/agents")
def agents_status():
    return {name: agent.status() for name, agent in AGENTS.items()}


@app.post("/api/agents/{name}/run")
async def run_agent(name: str):
    agent = AGENTS.get(name)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{name}'")
    try:
        return await agent.run()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{agent.title} failed: {e}")


DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    # React Router handles /devices, /compliance, ... in the browser,
    # so every other non-API path gets index.html.
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        file = DIST / path
        if path and file.is_file() and DIST in file.resolve().parents:
            return FileResponse(file)
        # no-cache so a rebuilt frontend shows up without a hard refresh
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
