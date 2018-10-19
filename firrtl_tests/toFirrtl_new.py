import pyrtl
from pyrtl import Input, Output, Register


def translate_to_firrtl(block, output_file, rom_blocks=None):
    f = open(output_file, "w+")
    # write out all the implicit stuff
    f.write("circuit Example : \n")
    f.write("  module Example : \n")
    f.write("    input clock : Clock\n    input reset : UInt<1>\n")
    # write out IO signals
    wireRegDefs = ""
    for wire in list(block.wirevector_subset()):
        if type(wire) == pyrtl.wire.Input:
            f.write("    input %s : UInt<%d>\n" % (wire.name, wire.bitwidth))
        elif type(wire) == pyrtl.wire.Output:
            f.write("    output %s : UInt<%d>\n" % (wire.name, wire.bitwidth))
        elif type(wire) == pyrtl.wire.WireVector:
            wireRegDefs += "    wire {} : UInt<{}>\n".format(wire.name, wire.bitwidth)
            # f.write("    wire %s : UInt<%d>\n" % (wire.name, wire.bitwidth))
        elif type(wire) == pyrtl.wire.Register:
            wireRegDefs += "    reg {} : UInt<{}>, clock\n".format(wire.name, wire.bitwidth);
            # f.write("    reg %s : UInt<%d>, clock\n" % (wire.name, wire.bitwidth))
        elif type(wire) == pyrtl.wire.Const:

            # some const is in the form like const_0_1'b1, is this legal operation?
            wire.name = wire.name.split("'").pop(0)
            wireRegDefs += "    node {} = UInt<{}>({})\n".format(wire.name, wire.bitwidth, wire.val)
        else:
            return 1
    f.write(wireRegDefs)
    f.write("\n")

    # write "Main"
    node_cntr = 0
    initializedMem = []
    for log_net in list(block.logic_subset()):
        if log_net.op == '&':
            f.write("    %s <= and(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == '|':
            f.write("    %s <= or(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == '^':
            f.write("    %s <= xor(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == 'n':
            f.write("    node T_%d = and(%s, %s)\n" % (node_cntr, log_net.args[0].name, log_net.args[1].name))
            f.write("    %s <= not(T_%d)\n" % (log_net.dests[0].name, node_cntr))
            node_cntr += 1
        elif log_net.op == '~':
            f.write("    %s <= not(%s)\n" % (log_net.dests[0].name, log_net.args[0].name))
        elif log_net.op == '+':
            f.write("    %s <= add(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == '-':
            f.write("    %s <= sub(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == '*':
            f.write("    %s <= mul(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == '=':
            f.write("    %s <= eq(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == '<':
            f.write("    %s <= lt(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == '>':
            f.write("    %s <= gt(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == 'w':
            f.write("    %s <= %s\n" % (log_net.dests[0].name, log_net.args[0].name))
        elif log_net.op == 'x':
            f.write("    %s <= mux(%s, %s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[2].name, log_net.args[1].name))
        elif log_net.op == 'c':
            f.write("    %s <= cat(%s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, log_net.args[1].name))
        elif log_net.op == 's':
            selEnd = log_net.op_param[0]
            if len(log_net.op_param) < 2:
                selBegin = selEnd
            else:
                selBegin = log_net.op_param[len(log_net.op_param)-1]
            f.write("    %s <= bits(%s, %s, %s)\n" % (log_net.dests[0].name, log_net.args[0].name, selBegin, selEnd))
        elif log_net.op == 'r':
            f.write("    %s <= mux(reset, UInt<%s>(0), %s)\n" % (log_net.dests[0].name, log_net.dests[0].bitwidth, log_net.args[0].name))
        elif log_net.op == 'm':
            # if there are rom blocks, need to be initialized
            if rom_blocks != None:
                if not log_net.op_param[0] in initializedMem:
                    initializedMem.append(log_net.op_param[0])

                    # find corresponding rom block according to memid
                    curr_rom = next((x for x in rom_blocks if x.id == log_net.op_param[0]), None)
                    f.write("    wire %s : UInt<%s>[%s]\n" % (log_net.op_param[1].name, log_net.op_param[1].bitwidth, 2**log_net.op_param[1].addrwidth))

                    # if rom data is a function, calculate the data first
                    if callable(curr_rom.data):
                        romdata = [curr_rom.data(i) for i in range(2**curr_rom.addrwidth)]
                        curr_rom.data = romdata

                    # write rom block initialization data
                    for i in range(len(curr_rom.data)):
                        f.write("    %s[%s] <= UInt<%s>(%s)\n" % (log_net.op_param[1].name, i, log_net.op_param[1].bitwidth, curr_rom.data[i]))

                # write the connection
                f.write("    %s <= %s[%s]\n" % (log_net.dests[0].name, log_net.op_param[1].name, log_net.args[0].name))

            else:
                if not log_net.op_param[0] in initializedMem:
                    initializedMem.append(log_net.op_param[0])
                    f.write("    cmem %s_%s : UInt<%s>[%s]\n" % (log_net.op_param[1].name, log_net.op_param[0], log_net.op_param[1].bitwidth, 2**log_net.op_param[1].addrwidth))
                f.write("    infer mport T_%d  = %s_%s[%s], clock\n" % (node_cntr, log_net.op_param[1].name, log_net.op_param[0], log_net.args[0].name))
                f.write("    %s <= T_%d\n" % (log_net.dests[0].name, node_cntr))
                node_cntr += 1
        elif log_net.op == '@':
            if not log_net.op_param[0] in initializedMem:
                initializedMem.append(log_net.op_param[0])
                f.write("    cmem %s_%s : UInt<%s>[%s]\n" % (log_net.op_param[1].name, log_net.op_param[0], log_net.op_param[1].bitwidth, 2**log_net.op_param[1].addrwidth))
            f.write("    when %s :\n" % log_net.args[2].name)
            f.write("      infer mport T_%d  = %s_%s[%s], clock\n" % (node_cntr, log_net.op_param[1].name, log_net.op_param[0], log_net.args[0].name))
            f.write("      T_%d <= %s\n" % (node_cntr, log_net.args[1].name))
            f.write("      skip\n")
            node_cntr += 1
        else:
            pass

    f.close()
    return 0


def generate_firrtl_test(sim_trace, working_block):
    inputs = working_block.wirevector_subset(Input)
    outputs = working_block.wirevector_subset(Output)
    registers = working_block.wirevector_subset(Register)

    test_str = "\t\tval tester = new InterpretiveTester(firrtlStr)\n"
    test_str += "\t\ttester.poke(\"reset\", 1)\n"
    test_str += "\t\ttester.step(1)\n"
    test_str += "\t\ttester.poke(\"reset\", 0)\n"
    for v in inputs.union(outputs).union(registers):
        test_str += "\t\tvar " + v.name + " = List(" + ",".join([str(sim_trace.trace[v.name][i]) for i in range(len(sim_trace))]) + ")\n"

    test_str += "\t\tfor (i <- 0 to " + str(len(sim_trace)) + " - 1) {\n"
    test_str += "\t\t\tprint(\"round \" + i + \"\\n\")\n"

    for i in inputs:
        test_str += "\t\t\ttester.poke(\"" + i.name + "\", " + i.name + "(i))\n"

    for o in outputs:
        test_str += "\t\t\ttester.expect(\"" + o.name + "\", " + o.name + "(i))\n"

    for r in registers:
        test_str += "\t\t\ttester.expect(\"" + r.name + "\", " + r.name + "(i))\n"

    test_str += "\t\t\ttester.step(1)\n"
    test_str += "\t\t}\n"

    return test_str


def wrap_firrtl_test(sim_trace, working_block, firrtl_str, test_name, firrtl_test_path):
    wrapper_str = "package firrtl_interpreter\n"
    wrapper_str += "import org.scalatest.{FlatSpec, Matchers}\n"
    wrapper_str += "class " + test_name + " extends FlatSpec with Matchers {\n"
    wrapper_str += "\tval firrtlStr: String =\n"
    wrapper_str += "\"\"\"\n"
    wrapper_str += firrtl_str
    wrapper_str += "\"\"\".stripMargin\n"
    wrapper_str += "\tit should \"run with InterpretedTester\" in {\n"
    wrapper_str += generate_firrtl_test(sim_trace, working_block)
    wrapper_str += "\t}\n"
    wrapper_str += "}\n"

    with open(firrtl_test_path + test_name + ".scala", "w") as f:
        f.write(wrapper_str)


