// Generated automatically via PyRTL
// As one initial test of synthesis, map to FPGA with:
//   yosys -p "synth_xilinx -top toplevel" thisfile.v

module toplevel(clk, rst, a, b, y);
    input clk;
    input rst;
    input[1:0] a;
    input[1:0] b;
    output[1:0] y;

    // Temporaries
    wire[2:0] tmp0;

    // Combinational logic
    assign tmp0 = (a + b);
    assign y = (tmp0[1:0]);
endmodule
