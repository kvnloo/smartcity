"""Load the machine-readable open/paid data catalog."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from smartcity.config import ROOT

CATALOG_PATH = ROOT / "data" / "catalog" / "datasets.json"


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def summary() -> dict:
    cat = load_catalog()
    datasets = cat.get("datasets") or []
    buckets: dict[str, int] = {}
    paid = []
    open_ok = []
    for row in datasets:
        access = str(row.get("access") or "unknown")
        buckets[access] = buckets.get(access, 0) + 1
        if access in {"paid", "paid_metered"}:
            paid.append(
                {
                    "id": row["id"],
                    "theme": row.get("theme"),
                    "approximate_with": row.get("approximate_with"),
                    "notes": row.get("notes"),
                }
            )
        elif access in {"open", "open_partial", "open_html", "open_metered", "research"}:
            open_ok.append({"id": row["id"], "theme": row.get("theme"), "access": access})
    return {
        "region": cat.get("region"),
        "stack": cat.get("stack"),
        "counts": buckets,
        "open": open_ok,
        "paid_approximations": paid,
        "datasets": datasets,
    }
