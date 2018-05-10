import re

global global_index

def read_and_parse(fname):
    with open(fname) as f:
        content = f.readlines()
        result = []
        for x in content:
            matchObj = re.match('(.*) <-- (.*) -- (.*)', x)
            result.append([matchObj.group(1).strip(), matchObj.group(2).strip(), matchObj.group(3).strip()])
    return result

def translate_logical_ops(result):
    global_index = 15
    returnValue = []
    saveForLater = {}
    map = {}
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
            for arg in args:
                # if argument is register
                if re.match(".*/.*R", arg):
                    map[arg] = "_T_" + str(global_index)
                    returnValue.append("    reg " + map[arg] + " : UInt<" + re.match(".*/(.*)R", arg).group(1) + ">, clock with : \n"
                        "      reset => (UInt<1>(\"h0\"), " + map[arg] + ")")
                    global_index += 1
                    #print(map)

            # if the destination is W
            if re.match(".*/.*W", item[0]):
                map[item[0]] = "_T_" + str(global_index)
                returnValue.append("    node " + map[item[0]] + " = add(" + map[args[0]] + ", " + map[args[1]] + ")")
                global_index += 1
                print(map)

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
                print(map)
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


def scanTopLevl(fname):
    inOutStr = []
    with open(fname) as f:
        content = f.readlines()
    for line in content:
        print(line)
        matchInput = re.match(".* (.*)/(.*)I.*", line)
        if (matchInput):
            inOutStr.append("    input io_" + matchInput.group(1) + " : UInt<" + matchInput.group(2) + ">")
        matchOutput = re.match("(.*)/(.*)O.*", line)
        if (matchOutput):
            inOutStr.append("    output io_" + matchOutput.group(1) + " : UInt<" + matchOutput.group(2) + ">")
    return inOutStr


infname = "/Users/shannon/Desktop/working_block.txt"
result = read_and_parse(infname)
#print(translate_logical_ops(result))
outfname = "/Users/shannon/Desktop/firrtl_result.txt"
with open(outfname, "w+") as f:
    f.write("circuit Example : \n")
    f.write("  module Example : \n")
    f.write("    input clock : Clock\n    input reset : UInt<1>\n")
    f.write("\n".join(scanTopLevl(infname)))
    f.write("\n\n")
    f.write("\n".join(translate_logical_ops(result)))
