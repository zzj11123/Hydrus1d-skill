#!/usr/bin/env python3
"""Score observed vs simulated HYDRUS-1D values."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def metrics(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    if not pairs:
        return {"n": 0, "rmse": None, "mae": None, "bias": None, "nse": None, "r2": None}
    obs = [p[0] for p in pairs]
    sim = [p[1] for p in pairs]
    errors = [s - o for o, s in pairs]
    n = len(pairs)
    mse = sum(error * error for error in errors) / n
    mae = sum(abs(error) for error in errors) / n
    bias = sum(errors) / n
    obs_mean = sum(obs) / n
    sim_mean = sum(sim) / n
    denom = sum((o - obs_mean) ** 2 for o in obs)
    nse = 1 - sum((s - o) ** 2 for o, s in pairs) / denom if denom else None
    sim_denom = sum((s - sim_mean) ** 2 for s in sim)
    if denom and sim_denom:
        corr = sum((o - obs_mean) * (s - sim_mean) for o, s in pairs) / math.sqrt(denom * sim_denom)
        r2 = corr * corr
    else:
        r2 = None
    return {"n": n, "rmse": math.sqrt(mse), "mae": mae, "bias": bias, "nse": nse, "r2": r2}


def score(path: Path, group_by: list[str]) -> dict[str, Any]:
    rows = read_csv(path)
    all_pairs: list[tuple[float, float]] = []
    groups: dict[tuple[str, ...], list[tuple[float, float]]] = defaultdict(list)
    skipped = 0

    for row in rows:
        observed = as_float(row.get("observed"))
        simulated = as_float(row.get("simulated"))
        if observed is None or simulated is None:
            skipped += 1
            continue
        pair = (observed, simulated)
        all_pairs.append(pair)
        key = tuple(str(row.get(column, "")) for column in group_by)
        groups[key].append(pair)

    return {
        "path": str(path),
        "rows": len(rows),
        "scored": len(all_pairs),
        "skipped": skipped,
        "overall": metrics(all_pairs),
        "groups": [
            {"group": dict(zip(group_by, key)), "metrics": metrics(pairs)}
            for key, pairs in sorted(groups.items(), key=lambda item: item[0])
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score observed vs simulated values.")
    parser.add_argument("pairs_csv", help="CSV with observed and simulated columns.")
    parser.add_argument("--group-by", default="variable,depth_cm,solute_id", help="Comma-separated grouping columns.")
    args = parser.parse_args()
    group_by = [item.strip() for item in args.group_by.split(",") if item.strip()]
    result = score(Path(args.pairs_csv), group_by)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
