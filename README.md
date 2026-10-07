# Mengrui's project v7

GF180 **4x2 tiles, 80 MHz (12.5 ns), DELAY 0** controlled synthesis experiment.

The RTL is byte-identical to [v6 `dae8933`](https://github.com/BarryLee911/tt-gf-ucl-project-v6/commit/dae89331466486dab23fe0605b45c979ee50ef03).
Only the synthesis strategy changes from `AREA 0` to `DELAY 0`; the module, pins,
sampling schedule, reset, pipeline latency, floorplan and timing constraints are unchanged.

[Interface](docs/info.md) · [Experiment and results](docs/v7-delay0-comparison.md) ·
[Builds](https://github.com/BarryLee911/tt-gf-ucl-project-v7/actions)

`build_lock.json` records the pinned tools, PDK, constraints and all nine baseline STA corners.
The physical flow retains v6's original timing gates. A separate all-corner assessment
checks setup, hold and electrical violations. Functional gate-level regression does not use SDF.

Results: **DELAY 0 regressed setup and area**. Worst setup: −9.887542 ns (v6: −7.933554 ns); standard-cell area: +2.955%. RTL/GDS/precheck passed; functional gate-level regression failed at cycle 32; all-corner assessment failed. See the complete comparison and raw metrics above.

## Reproduce

Run the `gds` and `test` Actions workflows at the recorded experiment commit.
Documentation-only commits do not rebuild GDS; use workflow dispatch for intentional reruns.
The first experiment does not deploy a GitHub Pages layout viewer.
