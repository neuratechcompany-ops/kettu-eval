"""JSONL run storage — append-only, recoverable."""

from __future__ import annotations

import json
from pathlib import Path

from kettu_eval.core.models import RunRecord


class RunStorage:
    """Append-only JSONL storage for benchmark runs.

    Stores in `.kettu-eval/runs/` by default.
    """

    def __init__(self, base_dir: str | Path = ".kettu-eval/runs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.base_dir / "runs.jsonl"

    def write(self, run: RunRecord) -> None:
        with open(self._file, "a") as f:
            f.write(json.dumps(run.to_dict(), default=str) + "\n")

    def read_all(self) -> list[dict]:
        if not self._file.exists():
            return []
        records = []
        with open(self._file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def count(self) -> int:
        return len(self.read_all())

    def last(self) -> dict | None:
        records = self.read_all()
        return records[-1] if records else None

    def clear(self) -> None:
        if self._file.exists():
            self._file.unlink()
