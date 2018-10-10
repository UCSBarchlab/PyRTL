import pyrtl

def translate_to_FIRRTL(block,firrtl_file):
    f = open(firrtl_file, "w+")
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
    


