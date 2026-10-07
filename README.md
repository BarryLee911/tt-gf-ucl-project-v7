# Mengrui's project v7

GF180 **4x2 tiles, 80 MHz (12.5 ns), AREA 0** RTL timing optimization.

The current RTL derives from [v6 `dae8933`](https://github.com/BarryLee911/tt-gf-ucl-project-v6/commit/dae89331466486dab23fe0605b45c979ee50ef03).
The sampling divider is reduced from 27 to 23 bits, and peak-candidate selectors
are flattened to remove serial selection dependencies. The synthesis strategy
returns to `AREA 0`; module, pins, sampling schedule, reset, pipeline latency,
floorplan and timing constraints are unchanged. Candidate and baseline RTL
hashes are recorded separately in `build_lock.json`.

[Interface](docs/info.md) · [Previous DELAY 0 results](docs/v7-delay0-comparison.md) ·
[Builds](https://github.com/BarryLee911/tt-gf-ucl-project-v7/actions)

`build_lock.json` records the pinned tools, PDK, constraints and all nine baseline STA corners.
The physical flow retains v6's original timing gates. A separate all-corner assessment
checks setup, hold and electrical violations. Functional gate-level regression does not use SDF.

Previous results: **DELAY 0 regressed setup and area**. Worst setup: −9.887542 ns
(v6: −7.933554 ns); standard-cell area: +2.955%. RTL/GDS/precheck passed;
functional gate-level regression failed at cycle 32; all-corner assessment failed.
That experiment and its evidence remain available in the linked report.

The new AREA 0 experiment adds a before/after RTL regression checking pins and
peak state every cycle, all 24 divider levels, and a Yosys SAT proof of all 37
peak next-state bits from the actual RTL blocks. The existing three real
level-23 samples and independent pin-only RTL/gate regression are retained.

## Reproduce

Run the `gds` and `test` Actions workflows at the recorded experiment commit.
Documentation-only commits do not rebuild GDS; use workflow dispatch for intentional reruns.
The first experiment does not deploy a GitHub Pages layout viewer.
