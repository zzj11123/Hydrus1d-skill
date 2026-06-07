# Maintenance Notes

## Repository Layout

- `.codex-plugin/plugin.json`: Codex plugin manifest.
- `.mcp.json`: Plugin MCP server declaration.
- `hydrus1d_mcp_server.py`: Standalone MCP server for HYDRUS-1D.
- `skills/hydrus1d/SKILL.md`: Codex skill instructions.
- `skills/hydrus1d/references/`: Workflow and data references.
- `skills/hydrus1d/scripts/`: Data validation, output extraction, and scoring helpers.

## Release Checklist

1. Run Python syntax checks:

```powershell
python -m py_compile .\hydrus1d_mcp_server.py .\skills\hydrus1d\scripts\validate_observations.py .\skills\hydrus1d\scripts\extract_hydrus_outputs.py .\skills\hydrus1d\scripts\score_simulation.py
```

2. Validate the plugin manifest:

```powershell
python C:\path\to\validate_plugin.py .
```

3. Test a water-only project and a water-solute project.

4. Confirm `run_model` returns `success=true` for a completed project.

## Known HYDRUS-1D Notes

- HYDRUS-1D 4.xx command-line runs require `LEVEL_01.DIR` in the project directory.
- `Run_Inf.out` has different convergence-column positions for water-only and water-solute projects.
- The MCP server treats the original project as mutable only when the caller explicitly writes files; calibration workflows should copy the project first.
