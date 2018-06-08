import re


def initialize():
    global global_index
    global map
    global hasMem
    map = {}


def read_and_parse(contents):

    content = contents.split("\n")
    result = []
    for x in content:
        matchObj = re.match('(.*) <-- (.*) -- (.*)', x)
        result.append([matchObj.group(1).strip(), matchObj.group(2).strip(), matchObj.group(3).strip()])
    return result


def scan_in_out(contents):
    inOutStr = []
    content = contents.split("\n")
    for line in content:
        if bool(re.search(".*<-- m --/*", line)) | bool(re.search(".*<-- @ --/*", line)):
            matchInputs = re.findall(r'[a-zA-Z0-9-_]+/[0-9]+I', line)
            for str in matchInputs:
                if bool(matchInputs) & (not str in map):
                    map[str] = "io_" + str.split("/").pop(0)
                    inOutStr.append(
                        "    input " + map[str] + " : UInt<" + re.match(".*/([0-9]+)I", str).group(1) + ">")
            matchOutputs = re.findall(r'[a-zA-Z0-9-_]+/[0-9]+O', line)
            for str in matchOutputs:
                if bool(matchOutputs) & (not str in map):
                    map[str] = "io_" + str.split("/").pop(0)
                    inOutStr.append(
                        "    output " + map[str] + " : UInt<" + re.match(".*/([0-9]+)O", str).group(1) + ">")
        else:
            matchInput = re.match(".* ((.*)/(.*)I).*", line)
            if matchInput:
                if not (matchInput.group(1) in map):
                    map[matchInput.group(1)] = "io_" + matchInput.group(2)
                    inOutStr.append("    input io_" + matchInput.group(2) + " : UInt<" + matchInput.group(3) + ">")
            matchOutput = re.match("((.*)/(.*)O).*", line)
            if matchOutput:
                if not (matchOutput.group(1) in map):
                    inOutStr.append("    output io_" + matchOutput.group(2) + " : UInt<" + matchOutput.group(3) + ">")
                    map[matchOutput.group(1)] = "io_" + matchOutput.group(2)
    return inOutStr


def scan_regs(result):
    regs = []
    for line in result:
        matchReg = re.match("((.*)/.*)R", line[0])
        if (matchReg):
            if not re.match(".*\[.*", matchReg.group(2)):
                if not line[0] in map:
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


def translate_logical_ops(result, romDataList):
    returnValue = []
    saveForLater = {}
    global_index = 15
    hasMem = []

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

        elif item[1] == 'n':
            args = [x.strip() for x in item[2].split(", ")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + matchObj.group(2) + ")"

            # first do &
            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = and(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1

            # and then do ~
            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = not(" + "_T_" + str(global_index - 1) + ")")
            global_index += 1

        elif item[1] == '~':
            arg = item[2].strip()
            map[item[0]] = "_T_" + str(global_index)
            global_index += 1
            returnValue.append("    node " + map[item[0]] + " = not(" + map[arg] + ")")

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
            args = [x.strip() for x in item[2].split(", ")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + matchObj.group(2) + ")"

            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = eq(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1

        elif item[1] == '<':
            args = [x.strip() for x in item[2].split(", ")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + matchObj.group(2) + ")"

            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = lt(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1

        elif item[1] == '>':
            args = [x.strip() for x in item[2].split(", ")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + matchObj.group(2) + ")"

            map[item[0]] = "_T_" + str(global_index)
            returnValue.append("    node " + map[item[0]] + " = gt(" + map[args[0]] + ", " + map[args[1]] + ")")
            global_index += 1

        elif item[1] == 'w':
            matchReg = re.match("(.*)/[0-9]+[RO]", item[0])
            matchWire = re.match("(.*)/[0-9]+W", item[0])
            if matchReg:
                returnValue.append("    " + map[item[0]] + " <= " + map[item[2]])
            elif matchWire:
                if not item[0] in map:
                    map[item[0]] = "_T_" + str(global_index)
                    global_index += 1
                    returnValue.append("    node " + map[item[0]] + " = " + map[item[2]])
                else:
                    returnValue.append("    " + map[item[0]] + " = " + map[item[2]])

        elif item[1] == 'x':
            args = [x.strip() for x in item[2].split(",")]
            for arg in args:
                matchObj = re.match("const_(.*)_(.*)/([0-9]+)C", arg)
                if matchObj:
                    map[arg] = "UInt<" + matchObj.group(3) + ">(" + matchObj.group(2) + ")"

            # if the destination is W
            if re.match(".*/.*W", item[0]):
                map[item[0]] = "_T_" + str(global_index)
                returnValue.append("    node " + map[item[0]] + " = mux(" + map[args[0]] + ", " + map[args[2]] + ", " + map[args[1]] + ")")
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

#            print("current map is ", map)
#            print("current return string is", returnValue)

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
                if sel_list[1] == "":
                    sel_list.pop(1)
                after_sel = [binary_str[int(i)] for i in sel_list]
                map[item[0]] = after_sel
            else:
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
            returnValue.append(
                "    " + map[item[0]] + " <= " + "mux(reset, UInt<" + width + ">(\"h0\"), " + map[item[2]] + ")")

        # TODO: assumed no read enable for rom now
        elif item[1] == 'm':

            matchMem = re.match("(.*)\[(.*)\]\(memid=(.*)\)", item[2])
            memName = matchMem.group(1)     # name of the memory
            memRaddr = matchMem.group(2)    # read address of the memory
            memId = matchMem.group(3)       # memid of the memory

            matchMemDst = re.match(".*/([0-9]+)[A-Z]", item[0])
            memWidth = matchMemDst.group(1) # width of data inside memory

            matchAddr = re.match("[A-Za-z0-9_-]+/([0-9]+)[A-Z]", memRaddr)
            memAddrLen = matchAddr.group(1) # width of memory address

            if romDataList != None:
                if not memId in hasMem:
                    hasMem.append(memId)
                    returnValue.append("    wire " + memName + "_" + memId + " : UInt<" + memWidth + ">[" + str(2**int(memAddrLen)) + "]")
                    romData = romDataList[memName + "_" + memId]
                    for index in range(len(romData)):
                        returnValue.append("    " + memName + "_" + memId + "[" + str(index) + "] <= UInt<" + memWidth + ">(\"" + str(romData[index]) + "\")")
                map[item[0]] = "_T_" + str(global_index)
                global_index += 1
                returnValue.append(
                    "    _T_" + str(global_index) + " = " + memName + "_" + memId + "[" + map[
                        memRaddr] + "]")
                returnValue.append("    node " + map[item[0]] + " = _T_" + str(global_index))
                global_index += 1

            else:
                map[item[0]] = "_T_" + str(global_index)
                global_index += 1
                if not memId in hasMem:
                    hasMem.append(memId)
                    returnValue.append("    cmem " + memName + "_" + memId + " : UInt<" + memWidth + ">[" + str(
                        2**int(memAddrLen)) + "]")
                returnValue.append("    infer mport _T_" + str(global_index) + " = " + memName + "_" + memId + "[" + map[memRaddr] + "], clock")
                returnValue.append("    node " + map[item[0]] + " = _T_" + str(global_index))
                global_index += 1

        elif item[1] == '@':
            matchMem = re.match("(.*) .*=([a-zA-Z0-9-_]+/.*) \(memid=(.*)\)", item[2])
            memWdata = matchMem.group(1)
            memWe = matchMem.group(2)
            memId = matchMem.group(3)

            matchMemDst = re.match("(.*)\[(.*/([0-9]+)[A-Z])\]", item[0])
            memName = matchMemDst.group(1)
            memWaddr = matchMemDst.group(2)
            memAddrLen = matchMemDst.group(3)

            matchData = re.match(".*/([0-9]+)[A-Z]", memWdata)
            memWidth = matchData.group(1)

            if not memId in hasMem:
                hasMem.append(memId)
                returnValue.append("    cmem " + memName + "_" + memId + " : UInt<" + memWidth + ">[" + str(
                    2 ** int(memAddrLen)) + "]")

            returnValue.append("    when " + map[memWe] + " :")
            returnValue.append("      infer mport _T_" + str(global_index) + " = " + memName + "_" + memId + "[" + map[memWaddr] + "], clock")
            returnValue.append("      _T_" + str(global_index) + " <= " + map[memWdata])
            returnValue.append("      skip")
            global_index += 1
        else:
            print("illegal")

    for key in saveForLater.keys():
        returnValue.append("    " + map[key] + " <= " + map[saveForLater[key]])
    return returnValue


def main_translate(content, roms=None):
    initialize()
    result = read_and_parse(content)
    regs = scan_regs(result)
    outfname = "/Users/shannon/Desktop/firrtl_result.fir"

    if roms != None:
        romDataList = {}
        for rom in roms:
            list = []
            for index in range(2**rom.addrwidth):
                list.append(rom._get_read_data(index))
            romDataList[rom.name + "_" + str(rom.id)] = list
        print(romDataList)


    with open(outfname, "w+") as f:

        # write out all the implicit stuff
        f.write("circuit Example : \n")
        f.write("  module Example : \n")
        f.write("    input clock : Clock\n    input reset : UInt<1>\n")

        # write out input and output defined in PyRTL
        f.write("\n".join(scan_in_out(content)))
        f.write("\n\n")
        # write out registers

        for reg in regs:
            regName = reg.split("/").pop(0)
            regWidth = reg.split("/").pop(1)
            f.write("    reg " + regName + " : UInt<" + regWidth + ">, clock with : \n"
                            "      reset => (UInt<1>(\"h0\"), " + regName + ")\n")

        # write all the other logic
        f.write("\n".join(translate_logical_ops(result, romDataList)))
