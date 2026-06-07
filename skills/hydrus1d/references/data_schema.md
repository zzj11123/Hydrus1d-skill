# Observation Data Schema

Use this reference when validating Excel or CSV observations for HYDRUS-1D simulation comparison or calibration.

## Canonical Fields

Required:

- `time`: simulation time in the HYDRUS project time unit.
- `depth_cm`: observation depth below the soil surface in cm.
- `variable`: observed variable name.
- `observed`: observed numeric value.
- `unit`: observation unit.

Optional:

- `solute_id`: integer solute index, such as `1`, `2`, or `3`.
- `species`: solute or salt species label.
- `replicate`: replicate identifier.
- `weight`: numeric score weight.
- `group`: grouping label for calibration or validation.
- `note`: free-form note.

## Column Name Aliases

Time:

- `time`, `Time`, `t`, `day`, `days`, `时间`, `天数`

Depth:

- `depth_cm`, `depth`, `z`, `x`, `cm`, `深度`, `土层深度`, `观测深度`

Variable:

- `variable`, `var`, `type`, `指标`, `变量`, `项目`

Observed value:

- `observed`, `obs`, `value`, `measured`, `实测值`, `观测值`, `测定值`

Unit:

- `unit`, `units`, `单位`

Solute index:

- `solute_id`, `solute`, `solute_index`, `溶质编号`, `盐分编号`

Species:

- `species`, `ion`, `salt`, `solute_name`, `离子`, `盐分`, `溶质名称`

## Supported Variables

Water:

- `theta`
- `h`
- `water_content`
- `pressure_head`

Flux:

- `top_flux`
- `bottom_flux`
- `drainage`
- `cumulative_infiltration`

Solute/salinity:

- `concentration`
- `solute1`
- `solute2`
- `solute3`
- `EC`
- `TDS`
- `salt`

## Validation Rules

- Time must fall within the project `tInit` to `tMax` range unless the user explicitly allows extrapolation.
- Depth must fall inside the `PROFILE.DAT` soil profile.
- Solute/salinity observations should include `solute_id` or `species`. If neither exists, ask the user to map the observation to a HYDRUS solute output.
- Units must be checked against project units and user-provided measurement units. Do not silently convert EC, TDS, total salt, and ion concentration without a user-approved conversion.
