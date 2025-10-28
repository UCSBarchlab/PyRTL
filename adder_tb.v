module tb();
    reg clk;
    reg rst;

    // block Inputs
    reg[1:0] a;
    reg[1:0] b;

    // block Outputs
    wire[1:0] y;

    toplevel block(.clk(clk), .rst(rst), .a(a), .b(b), .y(y));

    always
        #5 clk = ~clk;

    initial begin
        $dumpfile ("waveform.vcd");
        $dumpvars;

        clk = 1'd0;
        rst = 1'd0;
        a = 2'd0;
        b = 2'd0;

        #10
        a = 2'd0;
        b = 2'd1;

        #10
        a = 2'd0;
        b = 2'd2;

        #10
        a = 2'd0;
        b = 2'd3;

        #10
        a = 2'd1;
        b = 2'd0;

        #10
        a = 2'd1;
        b = 2'd1;

        #10
        a = 2'd1;
        b = 2'd2;

        #10
        a = 2'd1;
        b = 2'd3;

        #10
        a = 2'd2;
        b = 2'd0;

        #10
        a = 2'd2;
        b = 2'd1;

        #10
        a = 2'd2;
        b = 2'd2;

        #10
        a = 2'd2;
        b = 2'd3;

        #10
        a = 2'd3;
        b = 2'd0;

        #10
        a = 2'd3;
        b = 2'd1;

        #10
        a = 2'd3;
        b = 2'd2;

        #10
        a = 2'd3;
        b = 2'd3;

        #10
        $finish;
    end
endmodule
