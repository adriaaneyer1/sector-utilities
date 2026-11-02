"""
AI Remediation Agent: brings non-compliant devices into compliance.

For every device that is not Compliant it runs, on its own:
  check version -> check firmware repository -> apply update -> reboot
  -> re-check compliance -> report

Devices that "Need change control" are never touched: changing their
firmware needs an approved change request first (NERC CIP-010-4), so the
agent only flags them.

The client's virtual devices can't be re-flashed, so an installed update is
recorded in the firmware state that the Compliance Agent applies on every
check. The reboot check is real: the agent waits until the device answers
again before re-checking it.

Run once from the command line:  python -m agents.remediation_agent
"""
import asyncio
import time

import config
from agents.base import Agent
from agents.compliance_agent import COMPLIANT, FIRMWARE_STATE, NEEDS_CHANGE_CONTROL, STATUSES
from agents.probes import TcpProbe

STAGES = ("check_version", "check_repository", "apply_update", "reboot", "recheck", "report")

# outcome per device
REMEDIATED = "remediated"
CHANGE_CONTROL = "change_control"
MANUAL = "manual"
FAILED = "failed"

REBOOT_ATTEMPTS = 5


class RemediationAgent(Agent):
    name = "remediation"
    title = "AI Remediation Agent"

    def __init__(self, store, compliance):
        super().__init__(store)
        self.compliance = compliance
        self.tcp = TcpProbe(config.CONNECT_TIMEOUT)
        self.progress = {}

    def status(self):
        """Adds each device's live stage so the page can animate the flow."""
        return {**super().status(), "progress": self.progress}

    async def execute(self):
        self.progress = {}
        self.step("Checking compliance of every device before remediation")
        before = await self.compliance.run()
        targets = [d for d in before["devices"] if d["status"] != COMPLIANT]
        self.step(f"{len(targets)} of {len(before['devices'])} device(s) need attention")
        for d in targets:
            self.progress[d["id"]] = {"name": d["name"], "stages": {s: {"state": "pending"} for s in STAGES}}

        repository = config.load_firmware_repository()
        installed = self.store.load(FIRMWARE_STATE) or {}
        outcomes = {}
        for d in targets:
            outcomes[d["id"]] = await self._remediate(d, repository, installed)
            self.store.save(FIRMWARE_STATE, installed)

        self.step("Re-checking compliance of every device")
        for d in targets:
            self._stage(d["id"], "recheck", "running")
        after = await self.compliance.run()
        after_by_id = {d["id"]: d for d in after["devices"]}

        results = []
        for d in targets:
            outcome, note = outcomes[d["id"]]
            new = after_by_id.get(d["id"], d)
            self._stage(d["id"], "recheck", "done", f"Now {new['status']}")
            self._stage(d["id"], "report", "done", note)
            self.step(f"'{d['name']}': {d['status']} -> {new['status']} ({note})")
            results.append({
                "id": d["id"],
                "name": d["name"],
                "type": d["type"],
                "protocol": d["protocol"],
                "endpoint": d["endpoint"],
                "company": d.get("company"),
                "sector": d.get("sector"),
                "location": d.get("location"),
                "outcome": outcome,
                "note": note,
                "before": {"status": d["status"], "firmware": d["firmware"], "findings": d["findings"]},
                "after": {"status": new["status"], "firmware": new["firmware"], "findings": new["findings"]},
                "stages": self.progress[d["id"]]["stages"],
            })

        count = lambda report: {s: sum(x["status"] == s for x in report["devices"]) for s in STATUSES}
        return {
            "summary": {
                "checked": len(before["devices"]),
                "targets": len(targets),
                "remediated": sum(o == REMEDIATED for o, _ in outcomes.values()),
                "change_control": sum(o == CHANGE_CONTROL for o, _ in outcomes.values()),
                "manual": sum(o in (MANUAL, FAILED) for o, _ in outcomes.values()),
                "before": count(before),
                "after": count(after),
            },
            "devices": results,
        }

    # ---------- one device ----------

    async def _remediate(self, d, repository, installed):
        """Walk one device through the flow; returns (outcome, note)."""
        name, dev_id = d["name"], d["id"]
        firmware = d["firmware"] or "unknown (requires login)"

        self._stage(dev_id, "check_version", "running")
        await self._pause()
        self._stage(dev_id, "check_version", "done", f"Running {firmware}")
        self.step(f"'{name}': firmware {firmware}, status {d['status']}")

        self._stage(dev_id, "check_repository", "running")
        await self._pause()
        entry = repository.get(d["category"]) or {}
        latest = entry.get("latest")

        if d["status"] == NEEDS_CHANGE_CONTROL:
            note = "Change approval required (NERC CIP-010-4): not remediated"
            self._stage(dev_id, "check_repository", "done", f"Approved version {latest}" if latest else "No approved version")
            return self._skip(dev_id, name, CHANGE_CONTROL, note)
        if not d["reachable"]:
            self._stage(dev_id, "check_repository", "done", "Device unreachable")
            return self._skip(dev_id, name, MANUAL, "Device unreachable: bring it back online first")
        open_codes = {f["code"] for f in d["findings"]}
        fixes = open_codes & set(entry.get("fixes", []))
        if not latest or not fixes:
            self._stage(dev_id, "check_repository", "done", "No firmware in the repository fixes these findings")
            return self._skip(dev_id, name, MANUAL, "Manual remediation required")
        self._stage(dev_id, "check_repository", "done", f"{latest} fixes {len(fixes)} of {len(open_codes)} finding(s)")
        self.step(f"'{name}': repository has {latest}, fixing {len(fixes)} finding(s)")

        self._stage(dev_id, "apply_update", "running", f"Installing {latest}")
        await self._pause(2)
        installed[dev_id] = {
            "firmware": latest,
            "previous_firmware": d["firmware"],
            "fixes": sorted(set(entry.get("fixes", []))),
            "at": time.time(),
        }
        self._stage(dev_id, "apply_update", "done", f"Installed {latest}")
        self.step(f"'{name}': installed {latest}")

        self._stage(dev_id, "reboot", "running", "Restarting")
        await self._pause()
        if not await self._back_online(d):
            self._stage(dev_id, "reboot", "failed", "Did not come back online")
            return FAILED, "Device did not come back online after reboot"
        self._stage(dev_id, "reboot", "done", "Back online")
        self.step(f"'{name}': rebooted, back online")
        return REMEDIATED, f"Updated {d['firmware']} -> {latest}" if d["firmware"] else f"Installed {latest}"

    def _skip(self, dev_id, name, outcome, note):
        for stage in ("apply_update", "reboot"):
            self._stage(dev_id, stage, "skipped", note if stage == "apply_update" else None)
        self.step(f"'{name}': {note}")
        return outcome, note

    async def _back_online(self, d):
        """Real check: TCP devices must accept a connection again. MQTT
        devices are confirmed by their telemetry in the re-check."""
        if d["protocol"] == "MQTT":
            return True
        host, port = d["endpoint"].rsplit(":", 1)
        for _ in range(REBOOT_ATTEMPTS):
            if await self.tcp.is_open(host, int(port)):
                return True
            await asyncio.sleep(1)
        return False

    def _stage(self, dev_id, stage, state, detail=None):
        self.progress[dev_id]["stages"][stage] = {"state": state, "detail": detail}

    @staticmethod
    async def _pause(steps=1):
        await asyncio.sleep(config.REMEDIATION_STEP_SECONDS * steps)


if __name__ == "__main__":
    import json
    import logging

    from agents.compliance_agent import ComplianceAgent
    from agents.store import ReportStore

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    store = ReportStore(config.REPORTS_DIR)
    report = asyncio.run(RemediationAgent(store, ComplianceAgent(store)).run())
    print(json.dumps(report["summary"], indent=2))
