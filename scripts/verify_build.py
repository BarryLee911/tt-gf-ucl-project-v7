"""Retain comparable routed-build evidence; assess all corners separately from flow gates."""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification' / 'build'
OUT.mkdir(parents=True, exist_ok=True)
lock = json.loads((ROOT / 'build_lock.json').read_text())
run = ROOT / 'runs' / 'wokwi'
provenance_failures = []
missing = []


def read_json(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def check(condition, message):
    if not condition:
        provenance_failures.append(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


resolved = read_json(run / 'resolved.json')
source_hash = digest(ROOT / 'src/project.v')
check(source_hash == lock['source_sha256'], 'Candidate RTL source hash differs from experiment lock')
for key, expected in lock['expected_constraints'].items():
    check(key in resolved and resolved[key] == expected,
          f'{key}: expected {expected!r}, got {resolved.get(key)!r}')
check(resolved.get('meta', {}).get('librelane_version') == lock['librelane_version'], 'LibreLane version differs')
check(lock['pdk_version'] in resolved.get('PDK_ROOT', ''), 'PDK version differs')
tools = subprocess.run(['git', '-C', str(ROOT / 'tt'), 'rev-parse', 'HEAD'], capture_output=True, text=True)
check(tools.returncode == 0 and tools.stdout.strip() == lock['support_tools_commit'], 'Support tools commit differs')
head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
imported_baseline = lock.get('imported_baseline_commit', lock['baseline_commit'])
ancestor = subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', imported_baseline, head])
check(ancestor.returncode == 0, 'Imported v6 baseline is not an ancestor')
if 'baseline_tree_sha' in lock:
    imported_tree = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', imported_baseline + '^{tree}'], capture_output=True, text=True)
    check(imported_tree.returncode == 0 and imported_tree.stdout.strip() == lock['baseline_tree_sha'], 'Imported v6 snapshot tree differs')
if 'baseline_source_sha256' in lock:
    baseline_source = subprocess.run(['git', '-C', str(ROOT), 'show', imported_baseline + ':src/project.v'], capture_output=True)
    check(baseline_source.returncode == 0 and
          hashlib.sha256(baseline_source.stdout).hexdigest().upper() == lock['baseline_source_sha256'],
          'Imported v6 RTL source hash differs')
history = read_json(ROOT / 'docs' / 'v7-delay0-results.json')
check(history.get('experiment_commit') == lock.get('delay0_experiment_commit'), 'Historical DELAY 0 result commit differs')

metrics_path = run / 'final' / 'metrics.csv'
metrics = {}
if metrics_path.is_file():
    with metrics_path.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                metrics[row['Metric']] = float(row['Value'])
            except ValueError:
                metrics[row['Metric']] = row['Value']
else:
    missing.append('Final metrics.csv missing')
    states = sorted(run.glob('*-openroad-stapostpnr/state_out.json'))
    if states:
        metrics = read_json(states[-1]).get('metrics', {})

sta_dirs = sorted(run.glob('*-openroad-stapostpnr'))
sta = sta_dirs[-1] if sta_dirs else None
if not sta:
    missing.append('Final routed STA missing')
constraints = sorted((run / 'final').rglob('*.sdc'))
if not constraints and sta:
    constraints = sorted(sta.glob('*.sdc'))
if constraints:
    sdc = constraints[0].read_text()
    delays = [float(v) for v in re.findall(r'set_(?:input|output)_delay\s+([\d.]+)', sdc)]
    check(bool(delays) and all(v == 2.5 for v in delays), 'Final IO delay differs from 2.5 ns')
    periods = [float(v) for v in re.findall(r'create_clock[^\n]*?-period\s+([\d.]+)', sdc)]
    check(bool(periods) and all(v == 12.5 for v in periods), 'Final clock differs from 12.5 ns')
else:
    missing.append('Final SDC missing')

netlists = sorted((run / 'final').rglob('*.v'))
netlist = netlists[0].read_text() if netlists else ''
if not netlists:
    missing.append('Final netlist missing')
cells = {}
for m in re.finditer(r'\b(gf180mcu_fd_sc_mcu7t5v0__\w+)\s+(\S+)\s*\((.*?)\);', netlist, re.S):
    q = re.search(r'\.Q\s*\(([^)]+)\)', m[3])
    if q:
        cells[m[2]] = q[1].strip().lstrip('\\')


def paths_for(corner):
    report = sta / corner / 'max.rpt' if sta else None
    if not report or not report.is_file():
        missing.append(f'{corner}: setup path report missing')
        return []
    paths = []
    for block in re.split(r'(?=Startpoint:)', report.read_text())[1:]:
        start = re.search(r'Startpoint:\s+(\S+)', block)
        end = re.search(r'Endpoint:\s+(\S+)', block)
        slack = re.search(r'([-\d.]+)\s+slack\s+\(', block)
        arrival = re.search(r'([-\d.]+)\s+data arrival time', block)
        if not (start and end and slack and arrival):
            continue
        instance = start[1]
        clk = re.search(r'([-\d.]+)\s+[\^v]\s+' + re.escape(instance) + r'/CLK\b', block)
        paths.append(dict(startpoint=instance, endpoint=end[1],
                          start_register=cells.get(instance), end_register=cells.get(end[1]),
                          slack_ns=float(slack[1]), data_arrival_ns=float(arrival[1]),
                          data_delay_ns=float(arrival[1]) - float(clk[1]) if clk else None))
    return paths


corners = []
for corner in lock['sta_corners']:
    def metric(name):
        return metrics.get(f'{name}__corner:{corner}')
    values = dict(setup_ns=metric('timing__setup__ws'), hold_ns=metric('timing__hold__ws'),
                  setup_tns_ns=metric('timing__setup__tns'), setup_violations=metric('timing__setup_vio__count'),
                  hold_violations=metric('timing__hold_vio__count'),
                  slew=metric('design__max_slew_violation__count'),
                  capacitance=metric('design__max_cap_violation__count'),
                  fanout=metric('design__max_fanout_violation__count'))
    if any(v is None for v in values.values()):
        missing.append(f'{corner}: incomplete metrics')
    if not sta or not (sta / corner / 'min.rpt').is_file():
        missing.append(f'{corner}: hold path report missing')
    annotation = read_json(sta / corner / 'filter_unannotated_metrics.json') if sta else {}
    unannotated = annotation.get(f'timing__unannotated_net_filtered__count__corner:{corner}')
    check(unannotated == 0, f'{corner}: unannotated functional nets {unannotated}')
    old = lock['baseline_corners'][corner]
    delay = next((c for c in history.get('corners', []) if c['corner'] == corner), {})
    paths = paths_for(corner)
    groups = {}
    for p in paths:
        endpoint = p['end_register'] or ''
        for group in ('peak_first', 'peak_second', 'prescale_count', 'running_sum', 'output_register'):
            if endpoint.startswith(group) and (group not in groups or p['slack_ns'] < groups[group]['slack_ns']):
                groups[group] = p
    corners.append(dict(corner=corner, **values, unannotated_functional_nets=unannotated,
                        baseline_setup_ns=old['setup_ns'], baseline_hold_ns=old['hold_ns'],
                        delay0_setup_ns=delay.get('setup_ns'), delay0_hold_ns=delay.get('hold_ns'),
                        setup_improvement_ns=values['setup_ns'] - old['setup_ns'] if values['setup_ns'] is not None else None,
                        worst_reported_path=min(paths, key=lambda p: p['slack_ns']) if paths else None,
                        reported_path_groups=groups))

physical_keys = ['magic__drc_error__count', 'design__lvs_error__count', 'route__drc_errors',
                 'antenna__violating__nets', 'antenna__violating__pins']
physical = {key: metrics.get(key) for key in physical_keys}
physical_pass = all(v == 0 for v in physical.values())
timing_pass = all(c['setup_ns'] is not None and c['setup_ns'] >= 0 and c['hold_ns'] is not None and c['hold_ns'] >= 0 for c in corners)
electrical_pass = all(c[k] == 0 for c in corners for k in ('slew', 'capacitance', 'fanout'))
area_key = 'design__instance__area__stdcell'
count_key = 'design__instance__count__stdcell'
comparison = {k: {'baseline': lock['baseline_metrics'][k], 'experiment': metrics.get(k),
                  'change': metrics[k] - lock['baseline_metrics'][k] if k in metrics else None}
              for k in (area_key, count_key, 'timing__setup__ws', 'timing__hold__ws', 'timing__setup_vio__count', 'timing__hold_vio__count')}
complete = metrics_path.is_file() and not missing and os.environ.get('GDS_BUILD_OUTCOME') == 'success'
result = dict(experiment=lock['experiment'], experiment_commit=head,
              workflow_run_id=os.environ.get('GITHUB_RUN_ID'), baseline_commit=lock['baseline_commit'],
              source_sha256=source_hash, comparable=not provenance_failures, build_complete=complete,
              baseline_source_sha256=lock.get('baseline_source_sha256'),
              delay0_experiment_commit=lock.get('delay0_experiment_commit'),
              physical_pass=physical_pass, timing_pass=timing_pass, electrical_pass=electrical_pass,
              signoff_pass=complete and not provenance_failures and physical_pass and timing_pass and electrical_pass,
              corners=corners, physical=physical, comparison=comparison, provenance_failures=provenance_failures,
              missing_evidence=missing, metrics=metrics,
              scope='Routed user-macro STA. Functional gate simulation is without SDF.')
(OUT / 'assessment.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
evidence = [ROOT / 'src/project.v', ROOT / 'src/config.json', ROOT / 'build_lock.json',
            run / 'resolved.json', metrics_path] + constraints + netlists
if sta:
    evidence += list(sta.rglob('*.rpt')) + list(sta.rglob('*.json'))
(OUT / 'evidence_sha256.json').write_text(json.dumps({str(p.relative_to(ROOT)): digest(p) for p in evidence if p.is_file()}, indent=2) + '\n')
lines = ['# ' + lock['experiment'] + ' 路由后评估', '',
         f"可比性：{result['comparable']}；构建完成：{complete}；物理检查：{physical_pass}；九角时序：{timing_pass}；电气规则：{electrical_pass}。", '',
         '| Corner | v6 AREA 0 setup ns | v7 DELAY 0 setup ns | 优化 AREA 0 setup ns | 对 v6 改善 ns | 优化 hold ns | Slew | Cap | Fanout |',
         '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
def fmt(v):
    return 'missing' if v is None else f'{v:.6f}'
for c in corners:
    lines.append('| ' + ' | '.join([c['corner']] + [fmt(c[k]) for k in ('baseline_setup_ns', 'delay0_setup_ns', 'setup_ns', 'setup_improvement_ns', 'hold_ns', 'slew', 'capacitance', 'fanout')]) + ' |')
lines += ['', '面积与单元数：', '', json.dumps(comparison, indent=2), '',
          '检查问题：', ''] + ['- ' + x for x in provenance_failures + missing]
lines += ['', result['scope'], '']
(OUT / 'assessment.md').write_text('\n'.join(lines), encoding='utf-8')
summary = os.environ.get('GITHUB_STEP_SUMMARY')
if summary:
    with open(summary, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines))
print(json.dumps({k: result[k] for k in ('comparable', 'build_complete', 'physical_pass', 'timing_pass', 'electrical_pass', 'provenance_failures', 'missing_evidence')}, indent=2))
raise SystemExit(0 if not provenance_failures and complete and physical_pass else 1)
