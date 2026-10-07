`timescale 1ns/1ps
`default_nettype none
// RTL-only long-divider check. No force, deposit, or accelerated DUT clock.
module tb_level23;
    localparam integer DIVISOR = 8388608;
    localparam integer TERMINAL = 8388607;
    reg clk = 0;
    always #6.25 clk = ~clk;
    reg rst_n = 0, ena = 1, external_drive0 = 1;
    reg [7:0] adc = 128, external_data = 31;
    wire [7:0] data_out, io_out, io_oe, pads;
    wire [7:0] external_oe = external_drive0 ? 8'h1f : 8'h1e;
    genvar bit_index;
    generate for(bit_index=0; bit_index<8; bit_index=bit_index+1) begin: pins
        assign pads[bit_index] = external_oe[bit_index] ? external_data[bit_index] : 1'bz;
        assign pads[bit_index] = io_oe[bit_index] ? io_out[bit_index] : 1'bz;
    end endgenerate
    tt_um_sine_area_detector dut(
        .clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(adc), .uio_in(pads),
        .uo_out(data_out), .uio_out(io_out), .uio_oe(io_oe));

    integer cycles=0, elapsed=0, samples=0, processed=0, area=0, peak=0;
    integer expected_data=0, magnitude=0, count_expected=0;
    integer last_sample=0, interval_checks=0, reset_checks=0;
    integer latch_checks=0, invalid_checks=0, handoff_checks=0;
    integer first_elapsed=0, second_elapsed=0, third_elapsed=0;
    integer i, k, fd;
    reg configured=0, ready=0, kind=0, pending=0, capture=0;
    reg [7:0] pending_adc=0;
    reg dump_enabled=1;

    task step;
        input resetting;
        input [4:0] level;
        input [7:0] value;
        input drive0;
        begin
            @(negedge clk);
            rst_n=!resetting; external_data={3'b000,level}; adc=value;
            external_drive0=drive0; ena=(cycles%3 != 0);
            @(posedge clk);
            capture=0;
            if(resetting) begin
                configured=0; ready=0; kind=0; pending=0;
                elapsed=0; samples=0; processed=0; area=0; peak=0;
                expected_data=0; last_sample=0; interval_checks=0;
                reset_checks=reset_checks+1;
            end else begin
                // Independent small-sample model: three samples cannot expire.
                kind=ready && !kind;
                expected_data=kind ? peak : area;
                if(pending) begin
                    area=area+((pending_adc>=128)==((processed/1024)%2));
                    magnitude=pending_adc-128;
                    if(magnitude<0) magnitude=-magnitude;
                    if(magnitude>peak) peak=magnitude;
                    processed=processed+1;
                end
                pending=0;
                if(!configured) begin
                    if(level<=23) begin
                        if(level!=23) $fatal(1,"Dedicated test must configure level 23");
                        configured=1;
                        latch_checks=latch_checks+1;
                    end else invalid_checks=invalid_checks+1;
                end else begin
                    elapsed=elapsed+1;
                    capture=(elapsed % DIVISOR == 0);
                    if(capture) begin
                        if(elapsed-last_sample != DIVISOR) $fatal(1,"Wrong sample interval");
                        interval_checks=interval_checks+1;
                        last_sample=elapsed;
                        pending=1; pending_adc=value; samples=samples+1;
                        case(samples)
                            1:first_elapsed=elapsed;
                            2:second_elapsed=elapsed;
                            3:third_elapsed=elapsed;
                            default:$fatal(1,"Unexpected extra sample");
                        endcase
                        $display("LEVEL23_SAMPLE ordinal=%0d elapsed=%0d adc=%0d",samples,elapsed,value);
                    end
                    if(elapsed==80000) begin ready=1; handoff_checks=handoff_checks+1; end
                end
            end
            #0.001;
            cycles=cycles+1;
            if((^{data_out,io_out,io_oe})===1'bx) $fatal(1,"Unknown output cycle=%0d",cycles);
            if({data_out,io_out,io_oe} !==
               {expected_data[7:0],expected_data[10:8],4'b0000,kind,(ready ? 8'he1 : 8'he0)})
                $fatal(1,"Pin mismatch cycle=%0d elapsed=%0d actual=%h/%h/%h expected=%0d kind=%0d ready=%0d",
                       cycles,elapsed,data_out,io_out,io_oe,expected_data,kind,ready);
            if((external_oe & io_oe)!=0) $fatal(1,"Pin contention");
            if(ready && pads[0] !== kind) $fatal(1,"Resolved type pin mismatch");
            if(pads[7:5] !== io_out[7:5]) $fatal(1,"Resolved upper-data pins mismatch");
            count_expected=configured ? elapsed % DIVISOR : 0;
            if(dut.prescale_count !== count_expected[26:0] ||
               dut.config_latched_valid !== configured || dut.sample_valid !== capture ||
               dut.history_pointer !== samples[10:0])
                $fatal(1,"Divider/capture mismatch cycle=%0d elapsed=%0d",cycles,elapsed);
            if(configured && dut.prescale_terminal_latched !== 27'd8388607)
                $fatal(1,"Level 23 terminal must be 8388607");
            if(!resetting && cycles>1 && (dut.running_sum !== area[11:0] || dut.peak_first !== peak[7:0]))
                $fatal(1,"N+1 processing mismatch cycle=%0d",cycles);
        end
    endtask

    initial begin
        $dumpfile("level23.fst");
        $dumpvars(0,clk,rst_n,ena,adc,external_data,external_oe,pads,data_out,io_out,io_oe,
            elapsed,samples,processed,dut.prescale_count,dut.prescale_terminal_latched,
            dut.config_latched_valid,dut.sample_valid,dut.sample_magnitude,
            dut.sample_overlap,dut.sample_position,dut.history_pointer,
            dut.running_sum,dut.peak_first,dut.output_ready);
        repeat(4) step(1,31,128,1);
        for(i=24;i<32;i=i+1) step(0,i,127,1);
        step(0,23,128,1);
        if(samples!=0 || elapsed!=0) $fatal(1,"Configuration edge sampled");
        // Reset during the initial interval, then start a fresh full interval.
        repeat(257) step(0,0,255,0);
        step(1,31,128,0);
        step(0,23,128,1);
        if(samples!=0 || elapsed!=0) $fatal(1,"Immediate reconfiguration sampled");
        for(i=1;i<=3*DIVISOR+8;i=i+1) begin
            // Assertions run every edge; keep waves near events only.
            if(i==32 || i==80016 || (i % DIVISOR == 16)) begin $dumpoff; dump_enabled=0; end
            if(i==79984 || (i % DIVISOR == DIVISOR-16)) begin $dumpon; dump_enabled=1; end
            k=(i*73+19)%256; // Distractor ADC codes between sampling edges.
            if(i==DIVISOR) k=127;
            if(i==2*DIVISOR) k=0;
            if(i==3*DIVISOR) k=255;
            step(0,(i*7)%32,k,(i<16));
        end
        if(samples!=3 || processed!=3 || interval_checks!=3 ||
           first_elapsed!=8388608 || second_elapsed!=16777216 || third_elapsed!=25165824 ||
           area!=2 || peak!=128 || handoff_checks!=1 || invalid_checks!=8 || latch_checks!=2)
            $fatal(1,"Missing coverage or wrong three-sample result");
        // An active-design reset must also clear the pins immediately.
        step(1,31,128,0);
        step(0,23,128,1);
        repeat(8) step(0,0,255,0);
        if(samples!=0 || processed!=0 || !configured || reset_checks!=6 || latch_checks!=3)
            $fatal(1,"Active reset/reconfiguration failed");
        fd=$fopen("level23_results.json","w");
        if(!fd) $fatal(1,"Cannot write result");
        $fdisplay(fd,"{\"status\":\"PASS\",\"level\":23,\"divisor\":8388608,\"terminal\":8388607,");
        $fdisplay(fd,"\"cycles\":%0d,\"samples\":3,\"sample_edges_after_latch\":[8388608,16777216,25165824],",cycles);
        $fdisplay(fd,"\"clock_period_ns\":12.5,\"sample_interval_ns\":104857600,\"all_pins_checked_every_cycle\":true,");
        $fdisplay(fd,"\"forced_state\":false,\"reset_checks\":6,\"invalid_levels\":8,\"handoff_checks\":1,");
        $fdisplay(fd,"\"latch_checks\":3,\"pipeline_latency_checks\":\"PASS\",\"waveform\":\"event windows only; assertions always active\"}");
        $fclose(fd);
        $display("LEVEL23_PASS cycles=%0d samples=3 divisor=8388608 terminal=8388607 interval_checks=3",cycles);
        $finish;
    end
    initial begin #400000000; $fatal(1,"Simulation-time timeout"); end
endmodule
