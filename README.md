# Mengrui's project v6

GF180 sine sign-overlap and approximate peak detector. Target: **4x2 tiles,
80 MHz (12.5 ns), AREA 0**, TinyTapeout `ttgf26c`.

Levels **0–23 now all divide by 2^level**. Level 23 samples every 8,388,608 clocks
(104.8576 ms at 80 MHz), giving a 2048-sample reference frequency of 4.6566 mHz.
The old 0.5 mHz special case is removed. All other levels, the counter reset fix,
module interface, algorithms and pipeline latency remain unchanged.

[Interface](docs/info.md) · [Verification](docs/v6-verification.md) ·
[Builds](https://github.com/BarryLee911/tt-gf-ucl-project-v6/actions)

The engineering template is v5 `trial-4x2` at `d611e62`; the v5 repository is unchanged.
Local validation includes three full level-23 divider intervals with every-cycle
checks, unchanged-level regression and the independent pin-only cocotb tests.
GitHub's RTL workflow repeats the level-23 test; the official gate test retains
its existing levels 0/1/5 and receives the corrected reference-model divisor.

The current change gives the area accumulator one reset/process/hold assignment.
Local mapped-gate regression passes 460,637 cycles with explicit reset checks for
23 state signals (187 bits), and the three real level-23 samples are revalidated.
The preceding f4eab5f build failed GL startup with running_sum[0] unknown; the older
0b3e894 build passed GL but had worst SS setup slack -9.011503 ns. This source needs
a new official cloud GL result. Area reduction and SS timing closure are not claimed. No SDF simulation or relaxed timing constraints
are added. FPGA remains manual.
