"""Portable RTL-only level-23 check; snapshots, logs and event-window FST."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--compiler', default='iverilog')
    parser.add_argument('--vvp', default='vvp')
    args = parser.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    snap = out/'snapshot'
    snap.mkdir(exist_ok=False)
    for original, name in [(source, 'project.v'), (Path(__file__), 'run_level23.py'),
                           (Path(__file__).with_name('tb_level23.v'), 'tb_level23.v')]:
        shutil.copy2(original, snap/name)
    started = time.perf_counter()
    records = []
    result = {'status': 'FAIL', 'source_sha256': hashlib.sha256((snap/'project.v').read_bytes()).hexdigest().upper()}
    try:
        commands = [
            ('compile', [args.compiler, '-g2001', '-Wall', '-s', 'tb_level23', '-o', str(out/'sim.vvp'), str(snap/'project.v'), str(snap/'tb_level23.v')], 120),
            ('simulation', [args.vvp, str(out/'sim.vvp'), '-fst'], 1800),
        ]
        for name, cmd, timeout in commands:
            tick = time.perf_counter()
            with (out/(name+'.log')).open('w', encoding='utf-8') as log:
                proc = subprocess.run(cmd, cwd=out, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            records.append({'name': name, 'exit_code': proc.returncode, 'seconds': time.perf_counter()-tick})
            print(json.dumps(records[-1]), flush=True)
            if proc.returncode:
                raise RuntimeError(f'{name} failed; see {out/(name+".log")}')
        checks = json.loads((out/'level23_results.json').read_text())
        assert checks['status'] == 'PASS' and checks['samples'] == 3
        assert checks['sample_edges_after_latch'] == [8388608,16777216,25165824]
        assert checks['all_pins_checked_every_cycle'] and not checks['forced_state']
        assert (out/'level23.fst').stat().st_size > 0
        assert 'LEVEL23_PASS' in (out/'simulation.log').read_text()
        result.update(status='PASS', checks=checks)
    except Exception as error:
        result['failure'] = str(error)
    result.update(seconds=time.perf_counter()-started, commands=records)
    (out/'run_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
