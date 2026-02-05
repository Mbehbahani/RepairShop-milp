from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any


def read_schedule_data(src: str | Path | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(src, (str, Path)):
        with open(src, "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:                       # already a dict (unit tests)
        raw = src

    T        = {int(r): float(v) for r, v in raw["T"].items()}
    I        = {int(r): float(v) for r, v in raw["I"].items()}
    ST       = {int(r): int(v)   for r, v in raw["ST"].items()}
    OV_limit = {int(r): int(v)   for r, v in raw.get("OV_limit", {}).items()}

    d: Dict[int, Dict[int, int]] = {
        int(c): {int(j): int(dur) for j, dur in jobs.items()}
        for c, jobs in raw["d"].items()
    }

    e: Dict[int, Dict[int, int]] = {
        int(j): {int(r): int(ok) for r, ok in row.items()}
        for j, row in raw["e"].items()
    }

    return {"T": T, "I": I, "ST": ST, "OV_limit": OV_limit, "d": d, "e": e}