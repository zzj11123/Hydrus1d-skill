---
name: hydrus1d
description: "Use for HYDRUS-1D water flow, salinity, and solute transport work: inspecting HYDRUS-1D projects, validating Excel/CSV observations, running simulations through the hydrus1d MCP, calibrating parameters with user-provided bounds, comparing observed vs simulated values, and explaining results from SELECTOR.IN, PROFILE.DAT, ATMOSPH.IN, Run_Inf.out, Balance.out, Obs_Node.out, T_Level.out, and solute*.out files."
---

# HYDRUS-1D

Use this skill for HYDRUS-1D workflows involving water flow, salinity, or solute transport. Prefer the `mcp__hydrus1d` tools whenever they are available.

## Core Rules

- Default report language is Chinese. Keep HYDRUS file names, variable names, and units in English.
- Treat the original HYDRUS project as read-only during calibration or scenario testing. Copy the project first, then modify the copy.
- When creating, copying, or deriving a HYDRUS project, update the project description immediately after changing the scenario. Do not leave copied descriptions that no longer match the project.
- Do not invent calibration bounds. Ask the user for the parameter names and lower/upper bounds before running parameter searches.
- For coupled water and solute projects, calibrate water-flow parameters first, then solute/salinity parameters, unless the user explicitly requests joint calibration.
- Use structured evidence from files and outputs. Do not judge success from stdout alone.
- Never assume fixed `ATMOSPH.IN` column positions. Atmospheric-boundary column meanings must be inferred from the current project's `SELECTOR.IN`, `ATMOSPH.IN` structure, and consistency with the HYDRUS-1D GUI for that project.

## Project Creation And Scenario Metadata

When a task involves creating a new project, copying a project, renaming a project, or modifying a project into a new scenario:

1. Copy the base project first unless the user explicitly asks to edit the original.
2. Change the requested model inputs.
3. Update the project description files and fields that are present in the copied project, especially `DESCRIPT.TXT` and any title/heading/description text in HYDRUS project metadata files.
4. The description must reflect the actual scenario, not just the source project. Include the important changes such as:
   - project purpose
   - base project name
   - soil profile depth and discretization changes
   - water-flow boundary or initial-condition changes
   - solute/salinity settings, number of solutes, input concentration, pulse time, adsorption/reaction settings
   - parameters intentionally kept the same as the base project
   - date or short scenario tag when useful
5. Before running the new project, re-read the updated description and confirm it is consistent with `SELECTOR.IN`, `PROFILE.DAT`, and other modified files.

Example description for a derived project:

```text
Ponded_infiltr_test1: derived from Ponded_infiltr. Soil profile depth changed from 100 cm to 200 cm; original hydraulic parameters and boundary conditions retained unless otherwise noted.
```

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

## ATMOSPH.IN Editing Rules

When reading or modifying atmospheric boundary data:

1. Do not use a hard-coded column map for `ATMOSPH.IN`.
2. Determine the active atmospheric format from the current project by reading `SELECTOR.IN` flags and the actual `ATMOSPH.IN` header/table layout.
3. Cross-check the inferred columns against HYDRUS-1D GUI expectations for the same project setup. Column availability and meaning can change with options such as atmospheric boundary conditions, root water uptake, precipitation/evaporation inputs, variable boundary settings, and plant-growth options.
4. Before writing, produce an explicit column mapping for the current file, including the columns intended for `potET`, `LAI`, precipitation/irrigation, evaporation, transpiration, and any active solute or root-related atmospheric inputs.
5. If the mapping for `potET` or `LAI` is ambiguous, stop and ask the user to confirm the HYDRUS GUI column mapping or provide an exported/template `ATMOSPH.IN`.
6. After writing, re-read `ATMOSPH.IN` and verify that `potET` and `LAI` values actually landed in their intended columns. Do not rely on row length or script assumptions alone.
7. Report the verified column indexes/names and sample rows after modification.

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
