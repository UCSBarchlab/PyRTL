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

def scanInOut(fname):
    inOutStr = []
    with open(fname) as f:
        content = f.readlines()
    for line in content:
        matchInput = re.match(".* ((.*)/(.*)I).*", line)
        if (matchInput):
            map[matchInput.group(1)] = matchInput.group(2)
            inOutStr.append("    input io_" + matchInput.group(2) + " : UInt<" + matchInput.group(3) + ">")
        matchOutput = re.match("((.*)/(.*)O).*", line)
        if (matchOutput):
            inOutStr.append("    output io_" + matchOutput.group(2) + " : UInt<" + matchOutput.group(3) + ">")
            map[matchOutput.group(1)] = matchOutput.group(2)
    return inOutStr

def scanRegs(result):
    Regs = []
    for line in result:
        matchReg = re.match("(.*/.*)R", line[0])
        if (matchReg):
            Regs.append(matchReg.group(1))
            map[line[0]] = line[0].split("/").pop(0)
    return Regs

def translate_logical_ops(result):
    returnValue = []
    saveForLater = {}
    global_index = 15

    for item in result:
        if item[1] == '&':
            print("and")
        elif item[1] == '|':
            print("or")
        elif item[1] == '^':
            print('xor')
        elif item[1] == 'n':
            print("nand")
        elif item[1] == '~':
            print('flip')
        elif item[1] == '+':
            args = [x.strip() for x in item[2].split(",")]

            # if the destination is W
            if re.match(".*/.*W", item[0]):
                map[item[0]] = "_T_" + str(global_index)
                returnValue.append("    node " + map[item[0]] + " = add(" + map[args[0]] + ", " + map[args[1]] + ")")
                global_index += 1
                #print(map)

        elif item[1] == '-':
            print('sub')
        elif item[1] == '*':
            print("mul")
        elif item[1] == '=':
            print('eq')
        elif item[1] == '<':
            print("lt")
        elif item[1] == '>':
            print('gt')
        elif item[1] == 'w':
            saveForLater[item[0]] = item[2]
        elif item[1] == 'x':
            args = [x.strip() for x in item[2].split(",")]
            for arg in args:
                if (re.match(".*/.*I", arg)):
                    map[arg] = "io_" + re.match("(.*)/.*I", arg).group(1)

            # if the destination is W
            if re.match(".*/.*W", item[0]):
                map[item[0]] = "_T_" + str(global_index)
                returnValue.append("    node " + map[item[0]] + " = mux(" + map[args[0]] + ", " + map[args[1]] + ", " + map[args[2]] + ")")
                global_index += 1

        elif item[1] == 'c':
            matchObj = re.match("(.*), const_(.*)_(.*)/(.*)C", item[2])
            if matchObj:
                node = matchObj.group(1)
                const_index = matchObj.group(2)
                const_value = matchObj.group(3)
                const_width = matchObj.group(4)
                map[item[0]] = map.get(node)
                map[item[0]].extend(const_value)
                result_width = re.match(".*/(.*)W", item[0]).group(1)
                decimalUint = int("".join(map[item[0]]), 2)
                map[item[0]] = "UInt<" + result_width + ">(" + str(decimalUint) + ")"

                print(map)

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
                #print(map)
            else:
                # TODO
                matchObj = re.match("(.*) \(\((.*)\)\)", item[2])
                args = [x.strip() for x in matchObj.group(2).split(",")]
                map[item[0]] = "_T_" + str(global_index)
                returnValue.append("    node " + map[item[0]] + " = bits(" + map[matchObj.group(1)] + ", " + args[len(args)-1] + ", " + args[0] + ")")
                global_index += 1

        elif item[1] == 'r':
            returnValue.append("    " + map[item[0]] + " <= " + map[item[2]])
        else:
            print("illegal")

    for key in saveForLater.keys():
        returnValue.append("    io_" + re.match("(.*)/.*", key).group(1) + " <= " + map[saveForLater[key]])
    return returnValue


""" main starts here"""
initialize()
infname = "/Users/shannon/Desktop/working_block.txt"
result = read_and_parse(infname)
regs = scanRegs(result)
outfname = "/Users/shannon/Desktop/firrtl_result.txt"
with open(outfname, "w+") as f:

    # write out all the implicit stuff
    f.write("circuit Example : \n")
    f.write("  module Example : \n")
    f.write("    input clock : Clock\n    input reset : UInt<1>\n")

    # write out input and output defined in PyRTL
    f.write("\n".join(scanInOut(infname)))
    f.write("\n\n")

    # write out registers

    for reg in regs:
        regName = reg.split("/").pop(0)
        regWidth = reg.split("/").pop(1)
        f.write("    reg " + regName + " : UInt<" + regWidth + ">, clock with : \n"
                        "      reset => (UInt<1>(\"h0\"), " + regName + ")\n")

    # write all the other logic
    f.write("\n".join(translate_logical_ops(result)))
