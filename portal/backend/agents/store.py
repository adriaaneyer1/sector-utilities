"""Reports are plain JSON files, one per agent, so any tool can read them."""
import json
import os
from pathlib import Path


class ReportStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, name):
        return self.directory / f"{name}.json"

    def save(self, name, report):
        path = self._path(name)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(report, indent=2), encoding="utf-8")
        os.replace(tmp, path)  # atomic: readers never see a half-written file

    def load(self, name):
        try:
            return json.loads(self._path(name).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
