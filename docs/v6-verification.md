# v6 source and verification record

## Current revision: area accumulator reset priority (2026-09-23)

- RTL SHA256: `E070E8658952FF7314BFD6CE7E69E035233953CCCED5E57FA44714AE7D9F2FE2`.
- Parent: `f4eab5fe2214a925f541d9353d56f529aaaa1713`.
- Only running_sum assignment structure changes: one nonblocking assignment with
  reset, process, hold priority. Known-one guards retain procedural X/Z behavior.
- Keep level-23 divisor 8388608 and terminal 8388607, the counter reset fixes,
  ports, parameters, widths, algorithms, latency and GF180 / 4x2 / 80 MHz / AREA 0.
- No forced initialization, hand-edited mapped gates, keep/dont_touch attributes,
  or timing-constraint changes. Existing test algorithms and CI entries are unchanged.

### Actual checks of this source

| Check | Result |
|---|---|
| Icarus 12/13 compilation and wait parameters 80000/1/8/131072 | PASS |
| Original unchanged-level tests and frozen v4/v5 comparisons | PASS, 2294295 v5 pin comparisons |
| Independent cocotb levels 0/1/5, reset, saturation, expiry, refill, tie and contention | PASS, 460637 cycles |
| Before/after RTL all pins and running_sum compared every cycle | PASS, 460637 cycles |
| Level 23, three full real divider intervals, no forced state | PASS, 25166114 checked cycles |
| Level-23 sample edges after configuration | 8388608 / 16777216 / 25165824 |
| Newly mapped GF180 gate netlist against independent pin vectors | PASS, 460637 cycles |
| Explicit reset checks for 23 state signals / 187 bits | PASS, 14 frontend and 14 delayed-backend reset checks |
| Negative control: identical reset checks on unchanged failing f4eab5f cloud netlist | Rejected at cycle 2: running_sum[0]=X |

The 2048-bit overlap history remains intentionally unreset and is masked by window_full.
Pin X/Z, contention, mismatches, missing required coverage or waveforms fail the checks.
Snapshots, testbenches, vectors, logs, results and FST waves are retained locally.
Level 23 ran on Icarus 12 for 252.77 seconds: three samples, not a full
2048-sample reference period. Icarus 13 was used for compilation. The gate run used
Icarus 12; its source and freshly synthesized netlist were not force-initialized.

Mapped netlist SHA256: `C4841590DAC999D55902FC565A43A259D5D9A6920200D06E10F2645FFB47A016`.
Local synthesis uses Yosys 0.62 / 7326bb7d6 and the prior LibreLane command-sequence
translation with built-in opt, the filtered GF180 liberty, AREA 0 ABC script and
12.5 ns constraint. This is not the full GitHub/Nix physical flow or a claim of
byte-identical cloud mapping. A fresh official cloud GL result is still required.

### Previous cloud failure and current status

The [f4eab5f cloud build](https://github.com/BarryLee911/tt-gf-ucl-project-v6/actions/runs/35849624767)
passed RTL (including level 23), GDS generation and precheck but failed functional GL
at 75 ns, before legal configuration. Its running_sum[0] reset feedback propagated X.
The earlier 0b3e894 counter-reset build passed GL; that does not validate this source.
The new source has local validation above; cloud GL, physical area and timing results
are pending a new build. No SDF test is added and no timing constraint is relaxed.

---

All records below are historical, including statements about pending cloud runs.

## Historical revision: binary level 23 (2026-09-23)

- RTL SHA256: `E92D83617654FAFDB5C712BAE716938EEE275F5C86534E40D0021E3301213B9F`.
- Parent revision: `0b3e8946b57d24e7b2ec09fbf51dab8bb728a8b3`; its RTL SHA256 was
  `7A9D7C5D6CDF0ABF4E5A51DBAE152718059D2807431050BA6E699761C63840B9`.
- GF180, 4x2, 80 MHz / 12.5 ns, AREA 0; no constraint or port/parameter changes.
- Level 23 changes from 78,125,000 to 8,388,608 clocks per sample; terminal 8,388,607.
  All legal levels now use 2^level. Reference frequency: 4.656612873 mHz.
- Counter widths/reset fix, other levels, algorithms and output latency are retained.

### Actual local results for this SHA256

| Check | Result |
|---|---|
| Icarus 12/13 Verilog-2001 compilation, wait values 80000/1/8/131072, level-23 testbench | PASS |
| Level 23, Icarus 12, no forced state or accelerated sampling | PASS, 25,166,114 checked cycles, three real samples |
| Sampling edges relative to configuration | 8,388,608 / 16,777,216 / 25,165,824 |
| Every-cycle pins, X/Z, contention, divider, capture and pipeline checks | PASS |
| Invalid configuration, no sampling on latch, locked level, 80000-cycle handoff, reset/reconfiguration | PASS |
| Frozen v4/v5 comparison for unchanged levels | PASS, 2,294,295 v5 pin comparisons |
| Literal terminal checks | PASS, levels 0–22 in legacy bench plus level 23 in dedicated bench |
| Independent cocotb pin model, levels 0/1/5 and existing algorithm coverage | PASS, 460,637 cycles |
| Negative control using old special-divider source | Rejected as expected: incorrect level-23 terminal |

The long-divider run took 250.84 s locally. Its FST contains reset,
handoff and sample windows; assertions run on every tested clock. Only three level-23
samples were simulated, not a complete 2048-sample reference period. Icarus 13 was used
for compilation, not a second complete long run. Existing levels 0/1/5 retain saturation,
expiry, refill, tie, reset and zero/max coverage. The cocotb algorithm is unchanged;
only its level-23 divisor expression changes. Frozen historical RTL files are not edited.

A first short-regression attempt stopped because the sandbox could not read the local
cocotb runtime. The same tests passed when run with access to that runtime. Both attempts
and all source snapshots/logs/results/waves are retained locally; machine tools and large
waves are not repository content.

### Cloud scope

The RTL workflow adds `test/run_level23.py` with the dedicated RTL-only testbench;
the official pin-only gate tests remain levels 0/1/5. New cloud results are pending
at commit preparation. No local synthesis, GDS, gate or SDF run is claimed for this SHA.
The [parent cloud build](https://github.com/BarryLee911/tt-gf-ucl-project-v6/actions/runs/35716264155)
passed RTL, GDS, precheck and functional gate tests, with worst SS setup -9.011503 ns.
Those results are historical and do not validate the changed source. Constraints remain
unchanged; new area and timing require the new build reports.

---

The following record was written at the time of the previous revisions. References to
"current source" or pending cloud runs below belong to those historical dates and hashes.

## Historical revision: counter reset priority (2026-09-22)

- RTL SHA256: `7A9D7C5D6CDF0ABF4E5A51DBAE152718059D2807431050BA6E699761C63840B9`.
- Previous RTL SHA256: `AE377AFF09D813BD63B40F847447649CF1B8930161572D1E3C979158AD3ED169`.
- Baseline remains GF180 `gf180mcuD`, 4x2, 80 MHz / 12.5 ns, AREA 0.
- Only the update structure of `history_pointer` and `handoff_count` changes:
  each has one nonblocking assignment, selecting reset-to-zero, increment, or hold.
- Known-one enable comparisons preserve the original procedural-if behavior for X/Z.
- Top module, ports, parameters, algorithms, sample schedule and output latency remain
  unchanged. No additional registers, keep/dont_touch attributes, forced initial values,
  or hand-edited mapped cells are introduced.
- Level 23 retains its existing 78,125,000-clock divisor in this commit. The requested
  correction to 2^23 is a separate pending change, not part of this reset fix.

## Checks performed for the historical counter-reset source

| Check | Actual result |
|---|---|
| Original/current RTL, all outputs and both counters compared every cycle | PASS, 460,637 cycles, Icarus 12 |
| Newly synthesized GF180 netlist against unchanged independent model expectations | PASS, 460,637 cycles, Icarus 12 |
| Real divider levels 0 / 1 / 5 | PASS, 86,300 / 46,300 / 8,800 samples |
| Both counters zero after every reset edge in the gate-level run | PASS |
| Replay of original failing startup inputs through 512.501 ns | PASS, Icarus 12 and 13 |
| Independent mapped-netlist connectivity check | PASS, 0 problems |

The complete runs include illegal configuration, latch without immediate sampling,
default handoff, saturation/recovery, candidate expiry, refill, newer ties, reset,
pending-sample discard, and zero/max inputs. All output data, type and enables are
checked each cycle; X/Z, contention and mismatches fail. Source snapshots, logs,
vectors and waves were retained locally. Icarus 13 only ran the startup replay;
the complete regression is not claimed to have passed on both simulator versions.

Expected vectors came from the existing pin-only `test/test.py` reference model and
test sequence without changing their algorithms or expected values. The local Verilog
replay retains per-cycle output and contention checks. The repository's cloud cocotb
test, reference model and workflow files remain unchanged in this commit.

## Synthesis and physical scope

Local synthesis used Yosys 0.62 / `7326bb7d6` (YoWASP) and a command-sequence
translation of LibreLane 3.0.14, using built-in opt passes, the original build's
filtered GF180 liberty, AREA 0 ABC script and 12.5 ns constraint. This is not a run
of the complete GitHub/Nix physical flow. The unchanged RTL also failed startup in
this local flow, while the candidate passed; the local baseline's X timing differed
from the cloud baseline, so byte-identical mapping is not claimed.

New local mapped-netlist SHA256:
`AD297F6A172A64DBAC5A25364BB3CAAEAD193718C842BA9138906EC364C1DCE9`.
This netlist was generated from the revised RTL, without the earlier diagnostic
four-bit reset patch. Local synthesis area estimates are not post-layout measurements.

The [previous cloud build](https://github.com/BarryLee911/tt-gf-ucl-project-v6/actions/runs/35673421547)
at `c5d76616f5734e5cc554a01b73c093a09ba11d26` passed RTL, GDS generation and precheck,
but failed functional gate simulation; its worst SS setup slack was -8.757775 ns.
The current source has not yet completed a new physical build. SS timing closure,
physical area improvement, and a new cloud gate-level PASS are not claimed here.
No SDF simulation is added and no timing constraint is relaxed.

## Historical record: initial v6 source, not current-source validation

Everything below refers to the previous RTL hash and its initial upload record.
It is retained for provenance and does not replace the current checks above.

### Source and baseline

- v6 RTL SHA256: `AE377AFF09D813BD63B40F847447649CF1B8930161572D1E3C979158AD3ED169`.
- Template: `BarryLee911/tt-gf-ucl-project-v5`, `trial-4x2`, `d611e620a799619f136ed79b17ad873b106b6530`.
- Configuration: GF180 `gf180mcuD`, 4x2, 80 MHz / 12.5 ns, AREA 0.
- Placement density 60%, placement hold margin 0.5 ns, global-route hold margin 0.05 ns are retained.
- AREA 0 is explicitly pinned to the strategy recorded for the v5 baseline.
- Top module, external pins, parameters, and RTL bytes are unchanged from the local v6 source.

### Verified local run for this source

2026-09-21, level 5, real clock division, sine phase 37.5 degrees, 9.64 seconds.
The source snapshot SHA256 matches the uploaded RTL.

`PIPELINE_PASS,5,real,606360,18948,18948,263175,263175,65536,65536,2048,37.500000`

606,360 clock edges and 18,948 samples were checked. The run checked all output pins,
sample/processing pairing, an independent candidate model, sine and zero-input stages,
and 2,048 checks with ena low. Output frames: 263,175 area and 263,175 peak.
The original local run retains its complete snapshots, log and waveform; large artifacts
and machine-specific paths are not included here.

This is one verified case, not a claim that every level or the complete regression passed.
The older regression before the flat-if rewrite does not validate this source.

### Cloud validation

The inherited pin-only cocotb algorithm and expected values are unchanged; only the
version label in its report changes. RTL and functional gate-level tests retain levels
0, 1 and 5, illegal configuration, default handoff, saturation/recovery, candidate expiry,
buffer refill, newer ties, reset, pending-sample discard, and zero/max input cases.
Unknown outputs, pin contention, mismatches and missing required coverage fail the tests.

Actions runs RTL tests, GDS, precheck and functional gate-level checks on this revision.
FPGA remains manual. The GDS viewer uses the new repository's GitHub Pages.
SDF simulation is not included. No new physical PASS, area reduction or SS setup closure
is claimed before this revision's reports are available. TT setup and all-corner hold
checks remain enabled, with SS setup reported separately by the physical results.
