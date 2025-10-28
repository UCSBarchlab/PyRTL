// Generated automatically via PyRTL
// As one initial test of synthesis, map to FPGA with:
//   yosys -p "synth_xilinx -top toplevel" thisfile.v

module my_module (clk, rst, a, b, y);
    input clk;
    input rst;
    input a;
    input b;
    output y;

    // Combinational logic
    assign y = (a & b);
endmodule
