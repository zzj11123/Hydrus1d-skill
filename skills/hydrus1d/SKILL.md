---
name: hydrus1d
description: "Use for HYDRUS-1D water flow, salinity, and solute transport work: inspecting HYDRUS-1D projects, validating Excel/CSV observations, running simulations through the hydrus1d MCP, calibrating parameters with user-provided bounds, comparing observed vs simulated values, and explaining results from SELECTOR.IN, PROFILE.DAT, ATMOSPH.IN, Run_Inf.out, Balance.out, Obs_Node.out, T_Level.out, and solute*.out files."
---

# HYDRUS-1D

Use this skill for HYDRUS-1D workflows involving water flow, salinity, or solute transport. Prefer the `mcp__hydrus1d` tools whenever they are available.

## Core Rules

- Default report language is Chinese. Keep HYDRUS file names, variable names, and units in English.
- Treat the original HYDRUS project as read-only during calibration or scenario testing. Copy the project first, then modify the copy.
- Do not invent calibration bounds. Ask the user for the parameter names and lower/upper bounds before running parameter searches.
- For coupled water and solute projects, calibrate water-flow parameters first, then solute/salinity parameters, unless the user explicitly requests joint calibration.
- Use structured evidence from files and outputs. Do not judge success from stdout alone.

## Project Workflow

1. Inspect the project with `mcp__hydrus1d.inspect_project`.
2. Read `SELECTOR.IN` and identify:
   - `lWat = t`: water flow is active.
   - `lChem = t`: solute/salinity transport is active.
   - `No.Solutes`: number of solutes.
   - `LUnit`, `TUnit`, `MUnit`.
3. Read `PROFILE.DAT` for soil depth, node count, observation nodes, material/layer layout, and initial conditions.
4. If present, read `ATMOSPH.IN` for atmospheric boundary data.
5. Run with `mcp__hydrus1d.run_model(mode="auto")` unless the user only asked for inspection.
6. Validate success using:
   - `Run_Inf.out`: final convergence flag and iteration history.
   - `Balance.out`: final time, water-balance error, storage, top/bottom flux.
   - `solute*.out`: concentration transport outputs when `lChem = t`.

## Observation Data

For Excel/CSV observation data, first consult `references/data_schema.md`. Use `scripts/validate_observations.py` for field detection and data checks.

Default required fields:

- `time`
- `depth_cm`
- `variable`
- `observed`
- `unit`

Optional fields:

- `solute_id`
- `species`
- `replicate`
- `weight`
- `group`
- `note`

If automatic column mapping is ambiguous, ask the user to confirm the mapping before scoring or calibration.

## Analysis Guidance

For workflow details, read `references/hydrus1d_workflows.md`.

Water-flow analysis should cover:

- convergence and iteration behavior
- water-balance error
- storage change
- top and bottom fluxes
- wetting-front progress or steady-state behavior

Solute/salinity analysis should cover:

- active solute count and `solute*.out` files
- concentration peak and arrival time
- concentration by depth and time
- breakthrough behavior
- adsorption, retardation, reaction, or decay indications
- consistency between water movement and solute movement

For solute parameter meanings, read `references/solute_parameters.md`.

## Calibration Workflow

1. Confirm the target variables, observation data, scoring metric, and parameter bounds.
2. Validate the observation data.
3. Copy the base project for each trial.
4. Modify only the intended parameters in the copied project.
5. Run each trial.
6. Extract outputs with `scripts/extract_hydrus_outputs.py`.
7. Score simulations with `scripts/score_simulation.py`.
8. Report:
   - best parameter set
   - score table
   - failed runs and reasons
   - whether parameters are physically plausible
   - recommended next trial range

Default scoring metrics: RMSE, MAE, bias, NSE, and R2.

## Output Expectations

Default output should include:

- concise Chinese conclusion
- project type and assumptions
- key input settings
- run status and diagnostics
- water and/or solute result interpretation
- observed-vs-simulated score table when observations are provided
- CSV/Excel summary path when a file is generated
