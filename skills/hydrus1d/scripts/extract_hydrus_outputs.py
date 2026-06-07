#!/usr/bin/env python3
"""Extract common HYDRUS-1D output summaries as JSON or CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def parse_run_inf(path: Path) -> dict[str, Any]:
    rows = []
    if not path.exists():
        return {"exists": False, "rows": []}
    for line in read_text(path).splitlines():
        parts = line.split()
        if len(parts) >= 8 and parts[0].isdigit():
            if parts[8].upper() in {"T", "F"} if len(parts) > 8 else False:
                row = {
                    "tlevel": int(parts[0]),
                    "time": float(parts[1]),
                    "dt": float(parts[2]),
                    "iterations_water": int(parts[3]),
                    "iterations_solute": int(parts[4]),
                    "iterations": int(parts[3]) + int(parts[4]),
                    "itcum": int(parts[5]),
                    "kodt": parts[6],
                    "kodb": parts[7],
                    "converged": parts[8].upper() == "T",
                    "peclet": float(parts[9]) if len(parts) > 9 else None,
                    "courant": float(parts[10]) if len(parts) > 10 else None,
                }
            else:
                row = {
                    "tlevel": int(parts[0]),
                    "time": float(parts[1]),
                    "dt": float(parts[2]),
                    "iterations": int(parts[3]),
                    "itcum": int(parts[4]),
                    "kodt": parts[5],
                    "kodb": parts[6],
                    "converged": parts[7].upper() == "T",
                }
            rows.append(row)
    return {
        "exists": True,
        "rows": rows,
        "last": rows[-1] if rows else None,
        "max_iterations": max((row["iterations"] for row in rows), default=None),
    }


def grab(label: str, text: str) -> float | None:
    match = re.search(label + r"\s+([0-9.E+\-]+)", text)
    return float(match.group(1)) if match else None


def parse_balance(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "rows": []}
    text = read_text(path)
    blocks = re.split(r"-{10,}\s*\n Time\s+\[T\]\s+", text)[1:]
    rows = []
    for block in blocks:
        match = re.match(r"([0-9.E+\-]+)", block)
        if not match:
            continue
        rows.append(
            {
                "time": float(match.group(1)),
                "length": grab(r"Length\s+\[L\]", block),
                "w_volume": grab(r"W-volume \[L\]", block),
                "in_flow": grab(r"In-flow\s+\[L/T\]", block),
                "h_mean": grab(r"h Mean\s+\[L\]", block),
                "top_flux": grab(r"Top Flux \[L/T\]", block),
                "bottom_flux": grab(r"Bot Flux \[L/T\]", block),
                "watbal_abs": grab(r"WatBalT\s+\[L\]", block),
                "watbal_percent": grab(r"WatBalR\s+\[%\]", block),
            }
        )
    return {
        "exists": True,
        "rows": rows,
        "last": rows[-1] if rows else None,
        "max_abs_watbal_percent": max((abs(row["watbal_percent"] or 0) for row in rows), default=None),
    }


def parse_table(path: Path, max_rows: int | None = None) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "rows": []}
    rows = []
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower() == "end" or stripped.startswith(("*", "#", "-")):
            continue
        parts = re.split(r"\s+", stripped)
        if not parts or not re.match(r"^[+-]?[0-9.]", parts[0]):
            continue
        rows.append(parts)
        if max_rows is not None and len(rows) >= max_rows:
            break
    return {"exists": True, "rows": rows, "row_count_returned": len(rows)}


def extract(project: Path, max_table_rows: int = 200) -> dict[str, Any]:
    solute_files = sorted(project.glob("solute*.out"))
    return {
        "project": str(project),
        "run_inf": parse_run_inf(project / "Run_Inf.out"),
        "balance": parse_balance(project / "Balance.out"),
        "obs_node": parse_table(project / "Obs_Node.out", max_table_rows),
        "t_level": parse_table(project / "T_Level.out", max_table_rows),
        "solute_outputs": {path.name: parse_table(path, max_table_rows) for path in solute_files},
    }


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract HYDRUS-1D output summaries.")
    parser.add_argument("project", help="HYDRUS-1D project directory.")
    parser.add_argument("--max-table-rows", type=int, default=200)
    parser.add_argument("--balance-csv", help="Optional path to write Balance.out time series CSV.")
    args = parser.parse_args()
    result = extract(Path(args.project), args.max_table_rows)
    if args.balance_csv:
        write_csv_rows(Path(args.balance_csv), result["balance"]["rows"])
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
