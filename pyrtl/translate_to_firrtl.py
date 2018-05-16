import re

def initialize():
    global global_index
    global map
    map = {}


def read_and_parse(fname):
    with open(fname) as f:
        content = f.readlines()
        result = []
        for x in content:
            matchObj = re.match('(.*) <-- (.*) -- (.*)', x)
            result.append([matchObj.group(1).strip(), matchObj.group(2).strip(), matchObj.group(3).strip()])
    return result


def scan_in_out(fname):
    inOutStr = []
    with open(fname) as f:
        content = f.readlines()
    for line in content:
        matchInput = re.match(".* ((.*)/(.*)I).*", line)
        if matchInput:
            map[matchInput.group(1)] = "io_" + matchInput.group(2)
            inOutStr.append("    input io_" + matchInput.group(2) + " : UInt<" + matchInput.group(3) + ">")
        matchOutput = re.match("((.*)/(.*)O).*", line)
        if matchOutput:
            inOutStr.append("    output io_" + matchOutput.group(2) + " : UInt<" + matchOutput.group(3) + ">")
            map[matchOutput.group(1)] = "io_" + matchOutput.group(2)
    return inOutStr


def scan_regs(result):
    regs = []
    for line in result:
        matchReg = re.match("(.*/.*)R", line[0])
        if (matchReg):
            regs.append(matchReg.group(1))
            map[line[0]] = line[0].split("/").pop(0)
    return regs


# TODO: think about this
def convert_to_binary(str):
    matchBin = re.match(".*'b(.*)", str)
    matchHex = re.match(".*'h(.*)", str)
    matchDec = re.match("([0-9]+)", str)
    if matchBin:
        return matchBin.group(1)

    elif matchHex:
        return matchHex.group(1)
    elif matchDec:
        return matchDec.group(1)


def translate_logical_ops(result):
    returnValue = []
    saveForLater = {}
    global_index = 15

    for item in result:
        if item[1] == '&':
            args = [x.strip() for x in item[2].split(", ")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + matchObj.group(2) + ")"

            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = and(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1
            #print("current map is ", map)
            #print("current return string is", returnValue)
        elif item[1] == '|':
            args = [x.strip() for x in item[2].split(", ")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + matchObj.group(2) + ")"

            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = or(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1
        elif item[1] == '^':
            args = [x.strip() for x in item[2].split(", ")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + matchObj.group(2) + ")"

            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = xor(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1

        #TODO
        elif item[1] == 'n':
            print("nand")
        elif item[1] == '~':
            print('flip')
        elif item[1] == '+':
            args = [x.strip() for x in item[2].split(",")]
            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = add(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1
            #print(map)
        elif item[1] == '-':
            args = [x.strip() for x in item[2].split(",")]
            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = sub(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1
        elif item[1] == '*':
            args = [x.strip() for x in item[2].split(",")]
            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = mul(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1
        elif item[1] == '=':
            print('eq')
        elif item[1] == '<':
            print("lt")
        elif item[1] == '>':
            print('gt')
        elif item[1] == 'w':
            saveForLater[item[0]] = item[2]

        # TODO: simplify mux
        elif item[1] == 'x':
            args = [x.strip() for x in item[2].split(",")]

            # if the destination is W
            if re.match(".*/.*W", item[0]):
                map[item[0]] = "_T_" + str(global_index)
                returnValue.append("    node " + map[item[0]] + " = mux(" + map[args[0]] + ", " + map[args[1]] + ", " + map[args[2]] + ")")
                global_index += 1

        elif item[1] == 'c':
            args = [x.strip() for x in item[2].split(", ")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + convert_to_binary(matchObj.group(2)) + ")"
                elif isinstance(map[arg], list):
                    matchWidth = re.match(".*/([0-9]+)[A-Z]", arg)
                    if (matchWidth):
                        map[arg] = "UInt<" + matchWidth.group(1) + ">(" + str(int("".join(map[arg]), 2)) + ")"

            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = cat(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1

            print("current map is ", map)
            print("current return string is", returnValue)

        elif item[1] == 's':

            """ if select bits from a const or from a node """
            matchObj = re.match("const_(.*)_(.*)/(.*)C \(\((.*)\)\)", item[2])
            if matchObj:
                const_index = matchObj.group(1)
                const_value = matchObj.group(2)
                const_width = matchObj.group(3)
                const_sel = matchObj.group(4)
                binary_str = bin(int(const_value)).split("b").pop(1)
                sel_list = [x.strip() for x in const_sel.split(",")]
                after_sel = [binary_str[int(i)] for i in sel_list]
                map[item[0]] = after_sel
            else:
                # TODO
                matchObj = re.match("(.*) \(\((.*)\)\)", item[2])
                args = [x.strip() for x in matchObj.group(2).split(",")]
                map[item[0]] = "_T_" + str(global_index)
                if args[1] == "":
                    returnValue.append("    node " + map[item[0]] + " = bits(" + map[matchObj.group(1)] + ", " + args[0] + ", " + args[0] + ")")
                else:
                    returnValue.append("    node " + map[item[0]] + " = bits(" + map[matchObj.group(1)] + ", " + args[len(args)-1] + ", " + args[0] + ")")
                global_index += 1

            #print("current map is ", map)
            #print("current return string is", returnValue)
        elif item[1] == 'r':
            width = re.match(".*/([0-9]+).*", item[0]).group(1)
            returnValue.append("    " + map[item[0]] + " <= " + "mux(reset, UInt<" + width + ">(\"h0\"), " + map[item[2]] + ")")
        else:
            print("illegal")

    for key in saveForLater.keys():
        returnValue.append("    " + map[key] + " <= " + map[saveForLater[key]])
    return returnValue


""" main starts here"""
initialize()
infname = "/Users/shannon/Desktop/working_block1.txt"
result = read_and_parse(infname)
regs = scan_regs(result)
outfname = "/Users/shannon/Desktop/firrtl_result.fir"
with open(outfname, "w+") as f:

    # write out all the implicit stuff
    f.write("circuit Example : \n")
    f.write("  module Example : \n")
    f.write("    input clock : Clock\n    input reset : UInt<1>\n")

    # write out input and output defined in PyRTL
    f.write("\n".join(scan_in_out(infname)))
    f.write("\n\n")

    # write out registers

    for reg in regs:
        regName = reg.split("/").pop(0)
        regWidth = reg.split("/").pop(1)
        f.write("    reg " + regName + " : UInt<" + regWidth + ">, clock with : \n"
                        "      reset => (UInt<1>(\"h0\"), " + regName + ")\n")

    # write all the other logic
    f.write("\n".join(translate_logical_ops(result)))