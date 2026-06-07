#!/usr/bin/env python3
"""Minimal MCP server for controlling a local HYDRUS-1D installation.

The server intentionally has no third-party dependencies. It implements the
JSON-RPC subset used by MCP over stdio and exposes HYDRUS-1D operations as
tools.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.1.0"

DEFAULT_INSTALL_DIRS = [
    Path(r"C:\Program Files (x86)\PC-Progress\Hydrus-1D 4.xx"),
    Path(r"C:\Program Files\PC-Progress\Hydrus-1D 4.xx"),
    Path(r"C:\Program Files (x86)\PC-Progress\HYDRUS 2.xx"),
    Path(r"C:\Program Files\PC-Progress\HYDRUS 2.xx"),
]

INPUT_EXTENSIONS = {".in", ".dat", ".txt"}
OUTPUT_EXTENSIONS = {".out", ".log", ".err", ".txt"}
KNOWN_INPUTS = {
    "selector.in",
    "atmosph.in",
    "profile.dat",
    "level_01.dir",
    "meshtria.txt",
    "solute.in",
}
KNOWN_OUTPUTS = {
    "t_level.out",
    "nod_inf.out",
    "obs_node.out",
    "run_inf.out",
    "balance.out",
    "cum_q.out",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install-dir",
        default=os.environ.get("HYDRUS1D_INSTALL_DIR", ""),
        help="HYDRUS-1D installation directory.",
    )
    parser.add_argument(
        "--project-root",
        action="append",
        default=[],
        help="Allowed HYDRUS-1D project root. Can be passed multiple times.",
    )
    parser.add_argument(
        "--allow-any-project",
        action="store_true",
        help="Allow any project path on disk. Not recommended.",
    )
    return parser.parse_args()


ARGS = parse_args()


def default_project_roots() -> list[Path]:
    roots = [Path.cwd()]
    env_roots = os.environ.get("HYDRUS1D_PROJECT_ROOTS", "")
    for part in env_roots.split(";"):
        if part.strip():
            roots.append(Path(part.strip()))
    for root in ARGS.project_root:
        roots.append(Path(root))
    return [p.expanduser().resolve() for p in roots]


PROJECT_ROOTS = default_project_roots()


def find_install_dir() -> Path | None:
    if ARGS.install_dir:
        path = Path(ARGS.install_dir).expanduser()
        if path.exists():
            return path.resolve()
    for candidate in DEFAULT_INSTALL_DIRS:
        if candidate.exists():
            return candidate.resolve()
    return None


INSTALL_DIR = find_install_dir()


def exe_path(name: str) -> Path:
    if not INSTALL_DIR:
        raise ValueError("HYDRUS-1D installation directory was not found.")
    path = INSTALL_DIR / name
    if not path.exists():
        raise ValueError(f"Executable not found: {path}")
    return path


def ensure_under_roots(path: Path, roots: list[Path], label: str) -> Path:
    resolved = path.expanduser().resolve()
    if ARGS.allow_any_project:
        return resolved
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            pass
    allowed = ", ".join(str(root) for root in roots)
    raise ValueError(f"{label} is outside allowed roots. Path={resolved}; allowed={allowed}")


def project_path(value: str) -> Path:
    path = ensure_under_roots(Path(value), PROJECT_ROOTS, "Project path")
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Project directory does not exist: {path}")
    return path


def file_in_project(project: Path, relative_path: str, allowed_exts: set[str] | None = None) -> Path:
    if Path(relative_path).is_absolute():
        raise ValueError("Use a project-relative file path, not an absolute path.")
    path = (project / relative_path).resolve()
    try:
        path.relative_to(project)
    except ValueError as exc:
        raise ValueError("File path escapes the project directory.") from exc
    if allowed_exts and path.suffix.lower() not in allowed_exts:
        raise ValueError(f"File extension is not allowed: {path.suffix}")
    return path


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="")


def text_content(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


def json_content(value: Any) -> list[dict[str, str]]:
    return text_content(json.dumps(value, ensure_ascii=False, indent=2))


def ok(value: Any) -> dict[str, Any]:
    return {"content": json_content(value)}


def err(message: str) -> dict[str, Any]:
    return {"content": text_content(message), "isError": True}


def tool_schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
    }


TOOLS = [
    tool_schema(
        "find_installation",
        "Find the local HYDRUS-1D installation and executable paths.",
        {},
    ),
    tool_schema(
        "list_projects",
        "List likely HYDRUS-1D project directories under allowed project roots.",
        {
            "root": {"type": "string", "description": "Optional allowed root to scan."},
            "max_depth": {"type": "integer", "default": 4, "minimum": 0, "maximum": 8},
            "include_files": {"type": "boolean", "default": False},
            "limit": {"type": "integer", "default": 100, "minimum": 1, "maximum": 1000},
        },
    ),
    tool_schema(
        "inspect_project",
        "Inspect HYDRUS-1D input/output files in a project directory.",
        {"project_path": {"type": "string"}},
        ["project_path"],
    ),
    tool_schema(
        "read_input_file",
        "Read an input text file from a HYDRUS-1D project.",
        {
            "project_path": {"type": "string"},
            "relative_path": {"type": "string"},
            "max_chars": {"type": "integer", "default": 20000, "minimum": 1},
        },
        ["project_path", "relative_path"],
    ),
    tool_schema(
        "write_input_file",
        "Replace a HYDRUS-1D project input file. A .bak timestamp backup is created unless disabled.",
        {
            "project_path": {"type": "string"},
            "relative_path": {"type": "string"},
            "content": {"type": "string"},
            "backup": {"type": "boolean", "default": True},
        },
        ["project_path", "relative_path", "content"],
    ),
    tool_schema(
        "replace_in_input_file",
        "Perform literal or regex replacement in a HYDRUS-1D project input file.",
        {
            "project_path": {"type": "string"},
            "relative_path": {"type": "string"},
            "search": {"type": "string"},
            "replace": {"type": "string"},
            "regex": {"type": "boolean", "default": False},
            "backup": {"type": "boolean", "default": True},
            "count": {"type": "integer", "default": 0, "minimum": 0},
        },
        ["project_path", "relative_path", "search", "replace"],
    ),
    tool_schema(
        "run_model",
        "Run HYDRUS-1D calculation for a project by invoking H1D_CALC.EXE.",
        {
            "project_path": {"type": "string"},
            "mode": {
                "type": "string",
                "enum": ["auto", "cwd", "project_arg", "custom_args"],
                "default": "auto",
            },
            "custom_args": {"type": "array", "items": {"type": "string"}, "default": []},
            "timeout_seconds": {"type": "integer", "default": 600, "minimum": 1},
        },
        ["project_path"],
    ),
    tool_schema(
        "launch_gui",
        "Launch the HYDRUS-1D GUI. This does not automate clicks inside the GUI.",
        {
            "project_path": {"type": "string", "description": "Optional working directory."},
        },
    ),
    tool_schema(
        "read_output_file",
        "Read an output text file from a HYDRUS-1D project.",
        {
            "project_path": {"type": "string"},
            "relative_path": {"type": "string"},
            "max_chars": {"type": "integer", "default": 40000, "minimum": 1},
        },
        ["project_path", "relative_path"],
    ),
    tool_schema(
        "summarize_run",
        "Summarize common HYDRUS-1D output files and recent run status.",
        {"project_path": {"type": "string"}},
        ["project_path"],
    ),
    tool_schema(
        "parse_table_file",
        "Parse a whitespace-delimited HYDRUS-1D output/input table and return rows.",
        {
            "project_path": {"type": "string"},
            "relative_path": {"type": "string"},
            "skip_lines": {"type": "integer", "default": 0, "minimum": 0},
            "max_rows": {"type": "integer", "default": 200, "minimum": 1},
        },
        ["project_path", "relative_path"],
    ),
    tool_schema(
        "export_table_csv",
        "Parse a whitespace-delimited file and export it as CSV inside the project.",
        {
            "project_path": {"type": "string"},
            "relative_path": {"type": "string"},
            "csv_relative_path": {"type": "string"},
            "skip_lines": {"type": "integer", "default": 0, "minimum": 0},
        },
        ["project_path", "relative_path", "csv_relative_path"],
    ),
]


def list_likely_projects(root: Path, max_depth: int, include_files: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    root = ensure_under_roots(root, PROJECT_ROOTS, "Scan root")
    projects: list[dict[str, Any]] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        if depth > max_depth:
            dirs[:] = []
            continue
        lowered = {name.lower() for name in files}
        score = 0
        if "selector.in" in lowered:
            score += 5
        if "profile.dat" in lowered:
            score += 3
        if any(name.endswith(".out") for name in lowered):
            score += 1
        if score:
            item: dict[str, Any] = {"path": str(current_path), "score": score}
            if include_files:
                item["files"] = sorted(lowered)
            projects.append(item)
    projects.sort(key=lambda item: (-item["score"], item["path"]))
    return projects[:limit]


def inspect_project_impl(project: Path) -> dict[str, Any]:
    files = []
    for path in sorted(project.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        lowered = path.name.lower()
        role = "other"
        if lowered in KNOWN_INPUTS or suffix in INPUT_EXTENSIONS:
            role = "input"
        if lowered in KNOWN_OUTPUTS or suffix in OUTPUT_EXTENSIONS:
            role = "output" if suffix == ".out" or lowered in KNOWN_OUTPUTS else role
        files.append(
            {
                "name": path.name,
                "relative_path": path.name,
                "role": role,
                "size": path.stat().st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)),
            }
        )
    return {
        "project_path": str(project),
        "has_selector_in": (project / "Selector.in").exists() or (project / "SELECTOR.IN").exists(),
        "files": files,
    }


def backup_file(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.{stamp}.bak")
    backup.write_bytes(path.read_bytes())
    return backup


def parse_rows(text: str, skip_lines: int, max_rows: int | None = None) -> list[list[str]]:
    rows: list[list[str]] = []
    for index, line in enumerate(text.splitlines()):
        if index < skip_lines:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "*", ";")):
            continue
        parts = re.split(r"\s+", stripped)
        rows.append(parts)
        if max_rows is not None and len(rows) >= max_rows:
            break
    return rows


def summarize_run_impl(project: Path) -> dict[str, Any]:
    summary = inspect_project_impl(project)
    outputs = [f for f in summary["files"] if f["role"] == "output"]
    newest = sorted(outputs, key=lambda f: f["modified"], reverse=True)[:10]
    snippets: dict[str, str] = {}
    seen: set[str] = set()
    for name in ["Run_Inf.out", "RUN_INF.OUT", "T_Level.out", "T_LEVEL.OUT", "Balance.out", "BALANCE.OUT"]:
        path = project / name
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            text = read_text(path)
            snippets[path.name] = "\n".join(text.splitlines()[-40:])
    return {
        "project_path": str(project),
        "newest_outputs": newest,
        "snippets": snippets,
    }


def output_mtimes(project: Path) -> dict[str, float]:
    mtimes: dict[str, float] = {}
    for path in project.iterdir():
        if path.is_file() and path.suffix.lower() == ".out":
            mtimes[path.name] = path.stat().st_mtime
    return mtimes


def ensure_level_dir(project: Path) -> dict[str, Any]:
    path = project / "LEVEL_01.DIR"
    desired = str(project)
    previous = read_text(path).strip() if path.exists() else None
    changed = previous != desired
    if changed:
        path.write_text(desired, encoding="ascii")
    return {
        "path": str(path),
        "created": previous is None,
        "updated": changed and previous is not None,
        "content": desired,
    }


def parse_run_inf_row(parts: list[str]) -> dict[str, Any] | None:
    """Parse water-only and water-solute Run_Inf.out rows."""
    if len(parts) < 8 or not parts[0].isdigit():
        return None

    try:
        row: dict[str, Any] = {
            "tlevel": int(parts[0]),
            "time": float(parts[1]),
        }
    except ValueError:
        return None

    # Water-only format:
    # TLevel Time dt Iter ItCum KodT KodB Convergency
    if len(parts) >= 8 and parts[7].upper() in {"T", "F"}:
        row["converged"] = parts[7].upper() == "T"
        return row

    # Water-solute format:
    # TLevel Time dt ItrW ItrC ItCum KodT KodB Converg Peclet Courant
    if len(parts) >= 9 and parts[8].upper() in {"T", "F"}:
        row["converged"] = parts[8].upper() == "T"
        return row

    return None


def parse_completion(project: Path) -> dict[str, Any]:
    run_inf = project / "Run_Inf.out"
    balance = project / "Balance.out"
    result: dict[str, Any] = {
        "run_inf_exists": run_inf.exists(),
        "balance_exists": balance.exists(),
        "completed": False,
        "last_time": None,
        "last_tlevel": None,
        "last_converged": None,
        "max_abs_watbalr_percent": None,
        "final_watbalr_percent": None,
        "final_time": None,
    }
    if run_inf.exists():
        rows = []
        for line in read_text(run_inf).splitlines():
            row = parse_run_inf_row(line.split())
            if row is not None:
                rows.append(row)
        if rows:
            last = rows[-1]
            result["last_tlevel"] = last["tlevel"]
            result["last_time"] = last["time"]
            result["last_converged"] = last["converged"]
            result["completed"] = result["last_converged"]
    if balance.exists():
        text = read_text(balance)
        times = [float(match) for match in re.findall(r"Time\s+\[T\]\s+([0-9.E+\-]+)", text)]
        watbal = [float(match) for match in re.findall(r"WatBalR\s+\[%\]\s+([0-9.E+\-]+)", text)]
        if times:
            result["final_time"] = times[-1]
        if watbal:
            result["final_watbalr_percent"] = watbal[-1]
            result["max_abs_watbalr_percent"] = max(abs(value) for value in watbal)
    return result


def run_hydrus_command(command: list[str], project: Path, timeout_seconds: int) -> dict[str, Any]:
    level_dir = ensure_level_dir(project)
    before = output_mtimes(project)
    started = time.time()
    completed = subprocess.run(
        command,
        cwd=str(project),
        capture_output=True,
        input="\n",
        text=True,
        timeout=timeout_seconds,
        errors="replace",
    )
    after = output_mtimes(project)
    refreshed = sorted(name for name, mtime in after.items() if before.get(name) != mtime)
    completion = parse_completion(project)
    stdout = completed.stdout[-4000:]
    stderr = completed.stderr[-4000:]
    warning_lines = [
        line.strip()
        for line in (stdout + "\n" + stderr).splitlines()
        if line.strip() and ("does not exist" in line or "corrupted" in line or "warning" in line.lower())
    ]
    run_executed = bool(refreshed)
    success = completed.returncode == 0 and run_executed and completion.get("completed") is True
    return {
        "command": command,
        "cwd": str(project),
        "returncode": completed.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "success": success,
        "run_executed": run_executed,
        "level_dir": level_dir,
        "warnings": warning_lines,
        "refreshed_outputs": refreshed,
        "completion": completion,
        "stdout": stdout,
        "stderr": stderr,
        "summary": summarize_run_impl(project),
    }


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "find_installation":
            install = INSTALL_DIR
            return ok(
                {
                    "install_dir": str(install) if install else None,
                    "h1d_calc": str(install / "H1D_CALC.EXE") if install and (install / "H1D_CALC.EXE").exists() else None,
                    "hydrus_gui": str(install / "HYDRUS1D.EXE") if install and (install / "HYDRUS1D.EXE").exists() else None,
                    "allowed_project_roots": [str(root) for root in PROJECT_ROOTS],
                    "allow_any_project": ARGS.allow_any_project,
                }
            )

        if name == "list_projects":
            root_value = args.get("root")
            root = Path(root_value).expanduser() if root_value else PROJECT_ROOTS[0]
            return ok(
                {
                    "projects": list_likely_projects(
                        root,
                        int(args.get("max_depth", 4)),
                        bool(args.get("include_files", False)),
                        int(args.get("limit", 100)),
                    )
                }
            )

        if name == "inspect_project":
            return ok(inspect_project_impl(project_path(args["project_path"])))

        if name == "read_input_file":
            project = project_path(args["project_path"])
            path = file_in_project(project, args["relative_path"], INPUT_EXTENSIONS)
            text = read_text(path)
            max_chars = int(args.get("max_chars", 20000))
            return ok({"path": str(path), "content": text[:max_chars], "truncated": len(text) > max_chars})

        if name == "write_input_file":
            project = project_path(args["project_path"])
            path = file_in_project(project, args["relative_path"], INPUT_EXTENSIONS)
            backup = backup_file(path) if path.exists() and bool(args.get("backup", True)) else None
            write_text(path, args["content"])
            return ok({"path": str(path), "backup": str(backup) if backup else None, "bytes": path.stat().st_size})

        if name == "replace_in_input_file":
            project = project_path(args["project_path"])
            path = file_in_project(project, args["relative_path"], INPUT_EXTENSIONS)
            original = read_text(path)
            count = int(args.get("count", 0))
            if bool(args.get("regex", False)):
                updated, replacements = re.subn(args["search"], args["replace"], original, count=count)
            else:
                replacements = original.count(args["search"]) if count == 0 else min(count, original.count(args["search"]))
                updated = original.replace(args["search"], args["replace"], count)
            backup = backup_file(path) if bool(args.get("backup", True)) else None
            write_text(path, updated)
            return ok({"path": str(path), "backup": str(backup) if backup else None, "replacements": replacements})

        if name == "run_model":
            project = project_path(args["project_path"])
            calc = exe_path("H1D_CALC.EXE")
            mode = args.get("mode", "auto")
            timeout_seconds = int(args.get("timeout_seconds", 600))
            if mode in {"auto", "cwd"}:
                command = [str(calc)]
            elif mode == "custom_args":
                command = [str(calc)] + list(args.get("custom_args", []))
            else:
                command = [str(calc), str(project)]
            result = run_hydrus_command(command, project, timeout_seconds)
            result["mode"] = mode
            return ok(result)

        if name == "launch_gui":
            gui = exe_path("HYDRUS1D.EXE")
            cwd = str(project_path(args["project_path"])) if args.get("project_path") else str(INSTALL_DIR)
            process = subprocess.Popen([str(gui)], cwd=cwd)
            return ok({"pid": process.pid, "executable": str(gui), "cwd": cwd})

        if name == "read_output_file":
            project = project_path(args["project_path"])
            path = file_in_project(project, args["relative_path"], OUTPUT_EXTENSIONS)
            text = read_text(path)
            max_chars = int(args.get("max_chars", 40000))
            return ok({"path": str(path), "content": text[:max_chars], "truncated": len(text) > max_chars})

        if name == "summarize_run":
            return ok(summarize_run_impl(project_path(args["project_path"])))

        if name == "parse_table_file":
            project = project_path(args["project_path"])
            path = file_in_project(project, args["relative_path"])
            rows = parse_rows(read_text(path), int(args.get("skip_lines", 0)), int(args.get("max_rows", 200)))
            return ok({"path": str(path), "rows": rows, "row_count_returned": len(rows)})

        if name == "export_table_csv":
            project = project_path(args["project_path"])
            source = file_in_project(project, args["relative_path"])
            target = file_in_project(project, args["csv_relative_path"], {".csv"})
            rows = parse_rows(read_text(source), int(args.get("skip_lines", 0)), None)
            with target.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)
            return ok({"source": str(source), "csv": str(target), "rows": len(rows)})

        return err(f"Unknown tool: {name}")
    except subprocess.TimeoutExpired as exc:
        return err(f"HYDRUS-1D command timed out after {exc.timeout} seconds.")
    except Exception as exc:
        return err(f"{type(exc).__name__}: {exc}")


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "hydrus1d-mcp", "version": SERVER_VERSION},
            }
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = request.get("params", {})
            result = call_tool(params.get("name", ""), params.get("arguments", {}) or {})
        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(exc)}}


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = handle(request)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
