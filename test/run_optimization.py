"""Portable before/after RTL checks and SAT proof of the actual peak blocks.

The pin oracle is the existing independent Reference in test.py. Only its AST
and stimulus function are loaded, so local Icarus checks do not need cocotb.
No DUT state is forced. SAT covers binary combinational inputs; simulation
also rejects unknown output pins from the first reset edge.
"""
import argparse
import ast
from collections import Counter, deque
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def vectors(out):
    source = Path(__file__).with_name('test.py')
    tree = ast.parse(source.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))
             and n.name in ('Reference', 'stimulus')]
    assert len(nodes) == 2
    namespace = dict(Counter=Counter, deque=deque, math=math)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    Reference, stimulus = namespace['Reference'], namespace['stimulus']
    ref, cycles, coverage, levels = Reference(), 0, Counter(), []
    with (out/'vectors.hex').open('w', encoding='ascii') as f:
        def edge(adc=127, level=0, ena=1, reset=False, drive=True):
            nonlocal cycles
            ref.edge(reset, level, adc)
            expected = ((ref.data & 255) << 16) | (((ref.data >> 8) << 5 | ref.kind) << 8) | (0xe1 if ref.ready else 0xe0)
            inputs = (int(not reset) << 18) | (ena << 17) | (int(drive) << 16) | (adc << 8) | level
            f.write(f'{inputs << 24 | expected:011x}\n')
            cycles += 1

        for level in (0, 1, 5):
            ena_at = lambda: 1 if level == 0 else 0 if level == 1 else (cycles//17) % 2
            for _ in range(4):
                edge(reset=True, level=31, ena=ena_at(), drive=False)
            for invalid in range(24, 32):
                for _ in range(3):
                    edge(level=invalid, ena=ena_at())
            edge(level=level, ena=ena_at())
            assert ref.samples == 0
            start = None
            while start is None or ref.samples-start < 6300:
                if ref.ready and start is None:
                    start = ref.samples
                offset = -1 if start is None else ref.samples-start
                edge(stimulus(ref.samples, offset), (cycles*7)&31, ena_at(), drive=ref.elapsed < 16)
            for key in ('illegal_level', 'latch_without_sample', 'default_handoff',
                        'saturation', 'leave_saturation', 'expiry', 'buffer_refill',
                        'newer_tie', 'sample_1', 'sample_1024', 'sample_2047',
                        'sample_2048', 'sample_2049'):
                assert ref.cover[key], (level, key)
            coverage.update(ref.cover)
            levels.append(dict(level=level, samples=ref.samples, coverage=dict(ref.cover)))
        edge(reset=True, level=31, ena=0, drive=False)
        for _ in range(20):
            edge(level=0, ena=0)
        assert ref.samples == 19 and ref.processed == 18
        edge(reset=True, level=31, ena=0, drive=False)
        edge(adc=128, level=0, ena=0)
        for _ in range(24):
            edge(adc=128, level=31, ena=0, drive=False)
        assert ref.peak == 0
        edge(adc=0, level=31, ena=0, drive=False)
        edge(adc=255, level=31, ena=0, drive=False)
        edge(adc=128, level=31, ena=0, drive=False)
        # Long tied runs, position wrap, impulses, and deterministic noise.
        for index in range(8192):
            value = 0 if index in (1023, 1024, 2047, 2048) else 165 if index < 4096 else (index*73+19)&255
            edge(adc=value, level=(index*7)&31, ena=index&1, drive=False)
    return dict(cycles=cycles, levels=levels, coverage=dict(coverage),
                vector_sha256=sha(out/'vectors.hex'))


def peak_module(text, name):
    start = text.index('    /* Survival checks and parallel magnitude comparisons. */')
    end = text.index('    /* Output handoff:', start)
    return f'''module {name}(
input [7:0] sample_magnitude, peak_first, peak_second, peak_buffer,
input [10:0] sample_position,
input [9:0] peak_first_position, peak_second_position, peak_buffer_position,
input peak_history_valid, peak_second_valid,
output reg [7:0] peak_first_next, peak_second_next,
output reg [9:0] peak_first_position_next, peak_second_position_next,
output reg peak_second_valid_next);
''' + text[start:end] + '\nendmodule\n'


def miter(before, after):
    return peak_module(before, 'before_peak') + peak_module(after, 'after_peak') + '''
module peak_miter(
input [7:0] sample_magnitude, peak_first, peak_second, peak_buffer,
input [10:0] sample_position,
input [9:0] peak_first_position, peak_second_position, peak_buffer_position,
input peak_history_valid, peak_second_valid, output match);
wire [7:0] old_first, old_second, new_first, new_second;
wire [9:0] old_first_pos, old_second_pos, new_first_pos, new_second_pos;
wire old_valid, new_valid;
before_peak a(sample_magnitude,peak_first,peak_second,peak_buffer,sample_position,
peak_first_position,peak_second_position,peak_buffer_position,peak_history_valid,
peak_second_valid,old_first,old_second,old_first_pos,old_second_pos,old_valid);
after_peak b(sample_magnitude,peak_first,peak_second,peak_buffer,sample_position,
peak_first_position,peak_second_position,peak_buffer_position,peak_history_valid,
peak_second_valid,new_first,new_second,new_first_pos,new_second_pos,new_valid);
assign match = {old_first,old_second,old_first_pos,old_second_pos,old_valid} ==
               {new_first,new_second,new_first_pos,new_second_pos,new_valid};
endmodule
'''


def testbench(cycles):
    return r'''`timescale 1ps/1ps
module equivalence_tb;
reg clk=0,rst_n,ena,external_drive0;
reg [7:0] ui_in,uio_in;
wire [7:0] uo_out,uio_out,uio_oe,old_uo,old_uio,old_oe;
tri pad0;
wire [7:0] input_pins={uio_in[7:1],pad0};
assign pad0=external_drive0 ? uio_in[0] : 1'bz;
assign pad0=uio_oe[0] ? uio_out[0] : 1'bz;
tt_um_sine_area_detector dut(.clk(clk),.rst_n(rst_n),.ena(ena),.ui_in(ui_in),.uio_in(input_pins),.uo_out(uo_out),.uio_out(uio_out),.uio_oe(uio_oe));
tt_um_sine_area_detector_before original(.clk(clk),.rst_n(rst_n),.ena(ena),.ui_in(ui_in),.uio_in(input_pins),.uo_out(old_uo),.uio_out(old_uio),.uio_oe(old_oe));
reg [42:0] vectors[0:CYCLES-1];
reg [3:0] alive_cases=0;
integer i,fd;
initial begin
$readmemh("vectors.hex",vectors);
for(i=0;i<CYCLES;i=i+1)begin
clk=0;{rst_n,ena,external_drive0,ui_in,uio_in}=vectors[i][42:24];
#6250;
if(dut.backend_process === 1'b1) alive_cases[{dut.first_alive,dut.second_alive}]=1'b1;
clk=1;#6250;
if({uo_out,uio_out,uio_oe} !== vectors[i][23:0]) $fatal(1,"ORACLE cycle=%0d actual=%h expected=%h",i+1,{uo_out,uio_out,uio_oe},vectors[i][23:0]);
if({old_uo,old_uio,old_oe} !== {uo_out,uio_out,uio_oe}) $fatal(1,"EQUIVALENCE pins cycle=%0d",i+1);
if({original.peak_first,original.peak_second,original.peak_buffer,original.peak_first_position,original.peak_second_position,original.peak_buffer_position,original.peak_history_valid,original.peak_second_valid} !==
   {dut.peak_first,dut.peak_second,dut.peak_buffer,dut.peak_first_position,dut.peak_second_position,dut.peak_buffer_position,dut.peak_history_valid,dut.peak_second_valid}) $fatal(1,"EQUIVALENCE peak state cycle=%0d",i+1);
if(original.running_sum !== dut.running_sum || original.prescale_count !== dut.prescale_count || original.prescale_terminal_latched !== dut.prescale_terminal_latched) $fatal(1,"EQUIVALENCE sum/divider cycle=%0d",i+1);
if(external_drive0 && uio_oe[0]) $fatal(1,"CONTENTION cycle=%0d",i+1);
if(uio_oe[0] && pad0 !== uio_out[0]) $fatal(1,"PAD cycle=%0d",i+1);
end
if(alive_cases !== 4'hf) $fatal(1,"Missing alive-state cases: %b",alive_cases);
fd=$fopen("equivalence_checks.json","w");
$fdisplay(fd,"{\"status\":\"PASS\",\"cycles\":%0d,\"all_four_alive_cases\":true,\"all_pins_checked_every_cycle\":true,\"peak_state_checked_every_cycle\":true,\"forced_state\":false}",i);
$fclose(fd);
$display("EQUIVALENCE_PASS cycles=%0d alive_cases=%b",i,alive_cases);$finish;
end
endmodule
'''.replace('CYCLES', str(cycles))


def decoder_tb():
    return '''`timescale 1ps/1ps
module decoder_tb;
reg clk=0,rst_n=0;
reg [7:0] uio_in=31;
wire [7:0] uo_out,uio_out,uio_oe;
tt_um_sine_area_detector dut(.clk(clk),.rst_n(rst_n),.ena(1'b1),.ui_in(8'd128),.uio_in(uio_in),.uo_out(uo_out),.uio_out(uio_out),.uio_oe(uio_oe));
integer level,i,terminal,count;
task clock_step; begin #6250;clk=1;#6250;clk=0;end endtask
initial begin
if($bits(dut.prescale_count)!=23 || $bits(dut.prescale_terminal_latched)!=23 || $bits(dut.config_terminal)!=23) $fatal(1,"Wrong divider width");
for(level=0;level<=23;level=level+1)begin
rst_n=0;uio_in=31;clock_step;clock_step;
rst_n=1;uio_in=level;clock_step;
terminal=(1<<level)-1;
if(dut.prescale_terminal_latched !== terminal[22:0] || dut.prescale_count !== 23'd0 || dut.sample_valid !== 1'b0) $fatal(1,"Decode/latch level=%0d",level);
uio_in=31;count=0;
for(i=1;i<=8;i=i+1)begin
clock_step;
count=i % (1<<level);
if(dut.prescale_count !== count[22:0] || dut.sample_valid !== (count==0)) $fatal(1,"Initial interval level=%0d cycle=%0d",level,i);
if(dut.prescale_terminal_latched !== terminal[22:0]) $fatal(1,"Configuration changed level=%0d",level);
end
end
$display("DECODER_PASS levels=24 width=23 no_forced_state");$finish;
end
endmodule
'''


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--baseline-ref', default='0b31615fe098f962caa0cbd24dd1010ff01d4746')
    p.add_argument('--compiler', default='iverilog')
    p.add_argument('--vvp', default='vvp')
    p.add_argument('--sat', action='store_true')
    p.add_argument('--yosys-runner', type=Path)
    args=p.parse_args()
    source,out=args.source.resolve(),args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    before=subprocess.check_output(['git','-C',str(root),'show',args.baseline_ref+':src/project.v']).decode('utf-8')
    after=source.read_text(encoding='utf-8')
    (out/'before.v').write_text(before.replace('module tt_um_sine_area_detector #(', 'module tt_um_sine_area_detector_before #(',1),encoding='utf-8')
    shutil.copy2(source,out/'candidate.v')
    result=dict(status='FAIL',source_sha256=sha(out/'candidate.v'),baseline_ref=args.baseline_ref,
                baseline_source_sha256=hashlib.sha256(before.encode()).hexdigest().upper(),commands=[])
    started=time.perf_counter()
    try:
        result['vectors']=vectors(out)
        (out/'equivalence_tb.v').write_text(testbench(result['vectors']['cycles']),encoding='utf-8')
        (out/'decoder_tb.v').write_text(decoder_tb(),encoding='utf-8')
        commands=[('decoder_compile',[args.compiler,'-g2012','-Wall','-s','decoder_tb','-o','decoder.vvp','candidate.v','decoder_tb.v']),
                  ('decoder_simulation',[args.vvp,'decoder.vvp']),
                  ('equivalence_compile',[args.compiler,'-g2012','-Wall','-s','equivalence_tb','-o','equivalence.vvp','before.v','candidate.v','equivalence_tb.v']),
                  ('equivalence_simulation',[args.vvp,'equivalence.vvp'])]
        if args.sat:
            (out/'peak_miter.v').write_text(miter(before,after),encoding='utf-8')
            (out/'peak.ys').write_text('read_verilog peak_miter.v\nhierarchy -top peak_miter\nproc\nflatten\nopt\nsat -verify -prove match 1 -show-inputs -show-outputs\n',encoding='utf-8')
            yosys=[sys.executable,str(args.yosys_runner.resolve())] if args.yosys_runner else ['yosys']
            commands.append(('peak_sat',yosys+['-Q','-T','-s','peak.ys']))
        for name,cmd in commands:
            tick=time.perf_counter()
            with (out/(name+'.log')).open('w',encoding='utf-8') as log:
                proc=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
            record=dict(name=name,exit_code=proc.returncode,seconds=time.perf_counter()-tick)
            result['commands'].append(record)
            print(json.dumps(record),flush=True)
            if proc.returncode:
                raise RuntimeError(f'{name} failed; see {out/(name+".log")}')
        assert 'DECODER_PASS' in (out/'decoder_simulation.log').read_text()
        result['equivalence']=json.loads((out/'equivalence_checks.json').read_text())
        if args.sat:
            assert 'SUCCESS!' in (out/'peak_sat.log').read_text()
            result['peak_sat']='PASS: all binary inputs, 37 next-state bits, actual RTL blocks'
        result['status']='PASS'
    except Exception as error:
        result['failure']=str(error)
    result['seconds']=time.perf_counter()-started
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','source_sha256','seconds')},indent=2),flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
