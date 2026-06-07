# HYDRUS-1D Codex Plugin

This repository packages a local HYDRUS-1D MCP server and a Codex skill for
water-flow and salinity/solute transport workflows.

It is intended for Windows workstations with HYDRUS-1D installed locally.

## What It Provides

- A Codex plugin manifest: `.codex-plugin/plugin.json`
- A local MCP server declaration: `.mcp.json`
- A standalone MCP server: `hydrus1d_mcp_server.py`
- A Codex skill: `skills/hydrus1d/SKILL.md`
- Observation validation, HYDRUS output extraction, and scoring scripts.

## Capabilities

The MCP server can:

- Locate a local HYDRUS-1D installation.
- List HYDRUS-1D project folders under allowed roots.
- Inspect input and output files in a project.
- Read HYDRUS input and output files.
- Run `H1D_CALC.EXE` for a project.
- Launch the HYDRUS-1D GUI.
- Summarize run status from `Run_Inf.out` and `Balance.out`.
- Parse whitespace-delimited HYDRUS tables and export CSV files.

The Codex skill adds workflow guidance for:

- Water-flow project analysis.
- Salinity and solute-transport analysis.
- Excel/CSV observation validation.
- Observed-vs-simulated scoring.
- Semi-automatic calibration with user-provided parameter bounds.
- Chinese-language result interpretation while preserving HYDRUS file names,
  variables, and units in English.

## Requirements

- Windows.
- HYDRUS-1D 4.xx or compatible installation.
- Python 3.10 or newer.
- Optional: `openpyxl` for XLSX observation validation.

The MCP server itself uses only the Python standard library.

## Installation

See [docs/INSTALL.md](docs/INSTALL.md).

For a typical HYDRUS-1D 4.xx installation:

```powershell
$env:HYDRUS1D_INSTALL_DIR = "C:\Program Files (x86)\PC-Progress\Hydrus-1D 4.xx"
$env:HYDRUS1D_PROJECT_ROOTS = "C:\path\to\your\hydrus-project-root"
```

Then configure your MCP client to launch:

```powershell
python C:\path\to\hydrus1d\hydrus1d_mcp_server.py
```

## Direct Smoke Test

```powershell
python .\hydrus1d_mcp_server.py --install-dir "C:\Program Files (x86)\PC-Progress\Hydrus-1D 4.xx" --project-root "C:\path\to\your\hydrus-project-root"
```

Send MCP JSON-RPC lines on stdin:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"manual","version":"0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"find_installation","arguments":{}}}
```

## Security Model

By default, project operations are restricted to configured project roots.
Use `--allow-any-project` only on a trusted local workstation.

The server updates `LEVEL_01.DIR` before running `H1D_CALC.EXE`. That file is
required for clean HYDRUS-1D 4.xx command-line execution.

## Maintenance

See [docs/MAINTENANCE.md](docs/MAINTENANCE.md).

Before release:

```powershell
python -m py_compile .\hydrus1d_mcp_server.py .\skills\hydrus1d\scripts\validate_observations.py .\skills\hydrus1d\scripts\extract_hydrus_outputs.py .\skills\hydrus1d\scripts\score_simulation.py
```

```powershell
python C:\path\to\validate_plugin.py .
```

## License

MIT
