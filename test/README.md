# Interface tests

Run `make` for RTL or use the official GF workflow for gate-level tests.
The tests use external pins only, an independent 2048-sample area queue, and a peak candidate model.
Levels 0, 1, and 5 use real 80 MHz clocks and the default 80,000-clock handoff.
All output pins are checked from the first reset edge; X/Z fails.
The GF testbench connects VPWR/VGND. Functional simulation and physical timing are checked separately.

The v6 model captures a sample, updates statistics one clock later, and exposes them to the output on the next clock. Checks include a single-clock reset, pending-sample discard, zero/max magnitude and unchanged handoff timing.

The pin-only reference uses 2^level for every legal level, including 23.

## Level 23 long-divider RTL check

From the repository root run:

```
python test/run_level23.py --source src/project.v --output test/output/level23
```

Use a new output directory per run. Requires Python and Icarus (`iverilog`, `vvp`) on PATH.
This dedicated RTL bench checks three full 8,388,608-clock intervals with no forced
state. It checks all outputs every tested cycle and uses internal observations for
divider/capture/processing diagnostics; it is therefore not used against the gate netlist.
It checks reset, illegal levels, one-time latching, default handoff, sampling and pipeline
latency. Waves contain only event windows; checks are never gated by wave recording.
The independent model here covers three samples without expiry; existing cocotb and
unchanged-level regressions cover the longer algorithm scenarios.
Compile/run failure, timeout, X/Z, contention, missing coverage or missing waves fails.
The wrapper saves snapshots, logs, level23_results.json and run_results.json, and limits
the simulator to 1800 seconds. The RTL workflow runs it after the normal cocotb suite.
