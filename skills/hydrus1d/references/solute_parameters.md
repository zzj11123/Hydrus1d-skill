# Solute and Salinity Parameters

Use this reference when interpreting or calibrating HYDRUS-1D solute/salinity transport.

## Transport Controls

- `No.Solutes`: number of transported solutes.
- `Bulk.d.`: bulk density. Affects sorption and mass storage when adsorption is active.
- `DisperL.`: longitudinal dispersivity. Higher values broaden concentration fronts and breakthrough curves.
- `DifW`: molecular diffusion coefficient in water.
- `DifG`: diffusion coefficient in gas phase.
- `lTort`: tortuosity option.

## Sorption and Partitioning

- `Ks`: solute sorption/distribution parameter in the solute block. Do not confuse this with water-flow saturated hydraulic conductivity unless file context is clear.
- `Nu`: Freundlich or nonlinear sorption parameter, depending on model configuration.
- `Beta`: usually a partitioning or nonequilibrium-related coefficient depending on selected options.
- `Henry`: Henry coefficient for volatile or gas exchange behavior.

## Reaction and Decay

HYDRUS solute blocks may include first-order reaction or decay terms:

- `SnkL1`, `SnkS1`, `SnkG1`
- primed variants such as `SnkL1'`
- zero-order terms such as `SnkL0`, `SnkS0`, `SnkG0`
- `Alfa` in the solute block

Interpret these only after confirming the model option and solute meaning.

## Boundary and Pulse Inputs

- `kTopSolute`: top solute boundary type.
- `SolTop`: top solute concentration or input value.
- `kBotSolute`: bottom solute boundary type.
- `SolBot`: bottom solute concentration or output boundary value.
- `tPulse`: solute pulse duration.

## Calibration Guidance

- Calibrate water movement before solute transport when concentration movement depends strongly on flow timing.
- Use `DisperL.` for plume spreading and breakthrough curve width.
- Use `SolTop` and `tPulse` for input concentration and pulse timing uncertainty.
- Use sorption/reaction parameters only when observations show retardation, tailing, decay, or retention that flow and dispersion cannot explain.
- Do not convert EC, TDS, total salt, and ion concentration without an explicit user-approved conversion.
