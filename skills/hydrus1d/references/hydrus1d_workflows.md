# HYDRUS-1D Workflows

## Project Inspection

1. Inspect files with `mcp__hydrus1d.inspect_project`.
2. Read `SELECTOR.IN`.
3. Determine active modules:
   - `lWat = t`: water flow.
   - `lChem = t`: solute/salinity transport.
4. Extract units, material count, layer count, boundary conditions, time settings, and hydraulic parameters.
5. Read `PROFILE.DAT` for depth, nodes, observation nodes, initial pressure head/concentration, material and layer layout.
6. Read `ATMOSPH.IN` if atmospheric boundary conditions are active.

## Running a Model

Use `mcp__hydrus1d.run_model` with `mode="auto"`.

After running, verify:

- `success` is true.
- output files were refreshed.
- `Run_Inf.out` final convergence is true.
- `Balance.out` final time matches the requested simulation end.
- water-balance error is small enough for the use case.

## Water Result Analysis

Report:

- final time and convergence
- max and final water-balance error
- storage change
- top and bottom flux
- whether the profile is still transient or has reached steady state
- whether the wetting front reached the bottom boundary

## Solute/Salinity Result Analysis

For `lChem = t`, report:

- `No.Solutes`
- available `solute*.out` files
- concentration peak and arrival time when extractable
- concentration change by depth and time
- breakthrough behavior at observation nodes
- whether solute movement is consistent with water movement
- likely adsorption, retardation, dispersion, or reaction effects

For multi-solute projects, analyze each solute separately and then summarize combined behavior.

## Data Suitability Assessment

Before calibration, confirm:

- observation file format is readable
- required fields can be mapped
- variable names can be mapped to HYDRUS outputs
- times overlap simulation period
- depths overlap the profile
- solute observations include `solute_id` or `species`
- units and conversion assumptions are explicit

## Semi-Automatic Calibration

Default order:

1. Calibrate water-flow parameters.
2. Calibrate solute/salinity transport parameters.

Do not perform parameter search without user-provided bounds.

Water parameters:

- `thr`
- `ths`
- `Alfa`
- `n`
- `Ks`
- `l`

Solute parameters:

- `DisperL.`
- `DifW`
- `Bulk.d.`
- adsorption or partition parameters
- reaction or decay parameters
- `SolTop`
- `tPulse`

For each trial:

- copy the project
- modify the copy
- run the model
- extract outputs
- score against observations
- record parameters, status, and metrics

## Report Template

Use this structure by default:

1. `结论`
2. `项目类型与输入设置`
3. `运行状态`
4. `水分结果`
5. `盐分/溶质结果` when applicable
6. `实测-模拟对比` when observations are provided
7. `率定建议` when calibration is requested
