
"""
Contains functions to estimate aspects of blocks (like area and delay)
by either using internal models or by making calls out to external tool chains.
"""

from __future__ import print_function, unicode_literals

import re
import os
import math
import tempfile
import subprocess
import sys
import collections

from .core import working_block
from .wire import Input, Output, Const, Register, WireVector
from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .importexport import output_to_verilog
from .memory import RomBlock
from .helperfuncs import _currently_in_jupyter_notebook, _print_netlist_latex


# --------------------------------------------------------------------
#         __   ___          ___  __  ___              ___    __
#    /\  |__) |__   /\     |__  /__`  |  |  |\/|  /\   |  | /  \ |\ |
#   /~~\ |  \ |___ /~~\    |___ .__/  |  |  |  | /~~\  |  | \__/ | \|
#

def area_estimation(tech_in_nm=130, block=None):
    """ Estimates the total area of the block.

    :param tech_in_nm: the size of the circuit technology to be estimated
        (for example, 65 is 65nm and 250 is 0.25um)
    :return: tuple of estimated areas (logic, mem) in terms of mm^2

    The estimations are based off of 130nm stdcell designs for the logic, and
    custom memory blocks from the literature.  The results are not fully validated
    and we do not recommend that this function be used in carrying out science for
    publication.
    """

    def mem_area_estimate(tech_in_nm, bits, ports, is_rom):
        # http://www.cs.ucsb.edu/~sherwood/pubs/ICCD-srammodel.pdf
        # ROM is assumed to be 1/10th of area of SRAM
        tech_in_um = tech_in_nm / 1000.0
        area_estimate = 0.001 * tech_in_um**2.07 * bits**0.9 * ports**0.7 + 0.0048
        return area_estimate if not is_rom else area_estimate / 10.0

    # Subset of the raw data gathered from yosys, mapping to vsclib 130nm library
    # Width   Adder_Area  Mult_Area  (area in "tracks" as discussed below)
    # 8       211         2684
    # 16      495         12742
    # 32      1110        49319
    # 64      2397        199175
    # 128     4966        749828

    def adder_stdcell_estimate(width):
        return width * 34.4 - 25.8

    def multiplier_stdcell_estimate(width):
        if width == 1:
            return 5
        elif width == 2:
            return 39
        elif width == 3:
            return 219
        else:
            return -958 + (150 * width) + (45 * width**2)

    def stdcell_estimate(net):
        if net.op in 'w~sc':
            return 0
        elif net.op in '&|n':
            return 40 / 8.0 * len(net.args[0])   # 40 lambda
        elif net.op in '^=<>x':
            return 80 / 8.0 * len(net.args[0])   # 80 lambda
        elif net.op == 'r':
            return 144 / 8.0 * len(net.args[0])  # 144 lambda
        elif net.op in '+-':
            return adder_stdcell_estimate(len(net.args[0]))
        elif net.op == '*':
            return multiplier_stdcell_estimate(len(net.args[0]))
        elif net.op in 'm@':
            return 0  # memories handled elsewhere
        else:
            raise PyrtlInternalError('Unable to estimate the following net '
                                     'due to unimplemented op :\n%s' % str(net))

    block = working_block(block)

    # The functions above were gathered and calibrated by mapping
    # reference designs to an openly available 130nm stdcell library.
    # http://www.vlsitechnology.org/html/vsc_description.html
    # http://www.vlsitechnology.org/html/cells/vsclib013/lib_gif_index.html

    # In a standard cell design, each gate takes up a length of standard "track"
    # in the chip.  The functions above return that length for each of the different
    # types of functions in the units of "tracks".  In the 130nm process used,
    # 1 lambda is 55nm, and 1 track is 8 lambda.

    # first, sum up the area of all of the logic elements (including registers)
    total_tracks = sum(stdcell_estimate(a_net) for a_net in block.logic)
    total_length_in_nm = total_tracks * 8 * 55
    # each track is then 72 lambda tall, and converted from nm2 to mm2
    area_in_mm2_for_130nm = (total_length_in_nm * (72 * 55)) / 1e12

    # scaling from 130nm to the target tech
    logic_area = area_in_mm2_for_130nm / (130.0 / tech_in_nm) ** 2

    # now sum up the area of the memories
    mem_area = 0
    for mem in set(net.op_param[1] for net in block.logic_subset('@m')):
        bits, ports, is_rom = _bits_ports_and_isrom_from_memory(mem)
        mem_area += mem_area_estimate(tech_in_nm, bits, ports, is_rom)

    return logic_area, mem_area


def _bits_ports_and_isrom_from_memory(mem):
    """ Helper to extract mem bits and ports for estimation. """
    is_rom = False
    bits = 2**mem.addrwidth * mem.bitwidth
    read_ports = len(mem.readport_nets)
    write_ports = len(mem.writeport_nets)
    if isinstance(mem, RomBlock):
        is_rom = True
    ports = max(read_ports, write_ports)
    return bits, ports, is_rom


# --------------------------------------------------------------------
#   ___                 __        /\                     __      __
#    |  |  |\/| | |\ | /  `      /~~\ |\ |  /\  |  \_/  /__` |  /__`
#    |  |  |  | | | \| \__>     /    \| \| /~~\ |_  |   .__/ |  .__/
#

class TimingAnalysis(object):
    """
    Timing analysis estimates the timing delays in the block

    TimingAnalysis has an timing_map object that maps wires to the 'time'
    after a clock edge at which the signal in the wire settles
    """

    def __init__(self, block=None, gate_delay_funcs=None):
        """ Calculates timing delays in the block.

        :param block: pyrtl block to analyze
        :param gate_delay_funcs: a map with keys corresponding to the gate op and
            a function returning the delay as the value.
            It takes the gate as an argument.
            If the delay is negative (-1), the gate will be treated as the end
            of the block

        Calculates the timing analysis while allowing for
        different timing delays of different gates of each type.
        Supports all valid presynthesis blocks.
        Currently doesn't support memory post synthesis.
        """

        self.block = working_block(block)
        self.timing_map = None
        self.block.sanity_check()
        self._generate_timing_map(gate_delay_funcs)

    def _generate_timing_map(self, gate_delay_funcs):

        # The functions above were gathered and calibrated by mapping
        # reference designs to an openly available 130nm stdcell library.
        # Note that this is will compute the critical logic delay, but does
        # not include setup/hold time.

        if gate_delay_funcs is None:
            gate_delay_funcs = {
                '~': lambda width: 48.5,
                '&': lambda width: 98.5,
                '|': lambda width: 105.3,
                '^': lambda width: 135.07,
                'n': lambda width: 66.0,
                'w': lambda width: 0,
                '+': self._logconst_func(184.0, 18.9),
                '-': self._logconst_func(184.0, 18.9),
                '*': self._multiplier_stdcell_estimate,
                '<': self._logconst_func(101.9, 105.4),
                '>': self._logconst_func(101.9, 105.4),
                '=': self._logconst_func(60.1, 147),
                'x': lambda width: 138.0,
                'c': lambda width: 0,
                's': lambda width: 0,
                'r': lambda width: -1,
                'm': self._memory_read_estimate,
                '@': lambda width: -1,
            }
        cleared = self.block.wirevector_subset((Input, Const, Register))
        self.timing_map = {wirevector: 0 for wirevector in cleared}
        for _gate in self.block:  # ordered iteration
            if _gate.op == 'm':
                gate_delay = gate_delay_funcs['m'](_gate.op_param[1])  # reads require a memid
            else:
                gate_delay = gate_delay_funcs[_gate.op](len(_gate.args[0]))

            if gate_delay < 0:
                continue
            time = max(self.timing_map[a_wire] for a_wire in _gate.args) + gate_delay
            for dest_wire in _gate.dests:
                self.timing_map[dest_wire] = time

    @staticmethod
    def _logconst_func(a, b):
        return lambda x: a * math.log(float(x), 2) + b

    @staticmethod
    def _multiplier_stdcell_estimate(width):
        if width == 1:
            return 98.57
        elif width == 2:
            return 200.17
        else:
            return 549.1 * math.log(width, 2) - 391.7

    @staticmethod
    def _memory_read_estimate(mem):
        # http://www.cs.ucsb.edu/~sherwood/pubs/ICCD-srammodel.pdf
        # ROM is assumed to be same delay as SRAM (perhaps optimistic?)
        bits, ports, is_rom = _bits_ports_and_isrom_from_memory(mem)
        tech_in_um = 0.130
        return 270 * tech_in_um**1.38 * bits**0.25 * ports**1.30 + 1.05

    def max_freq(self, tech_in_nm=130, ffoverhead=None):
        """ Estimates the max frequency of a block in MHz.

        :param tech_in_nm: the size of the circuit technology to be estimated
            (for example, 65 is 65nm and 250 is 0.25um)
        :param ffoverhead: setup and ff propagation delay in picoseconds
        :return: a number representing an estimate of the max frequency in Mhz

        If a timing_map has already been generated by timing_analysis, it will be used
        to generate the estimate (and `gate_delay_funcs` will be ignored).  Regardless,
        all params are optional and have reasonable default values.  Estimation is based
        on Dennard Scaling assumption and does not include wiring effect -- as a result
        the estimates may be optimistic (especially below 65nm).
        """
        cp_length = self.max_length()
        scale_factor = 130.0 / tech_in_nm
        if ffoverhead is None:
            clock_period_in_ps = scale_factor * (cp_length + 189 + 194)
        else:
            clock_period_in_ps = (scale_factor * cp_length) + ffoverhead
        return 1e6 * 1.0 / clock_period_in_ps

    def max_length(self):
        """Returns the max timing delay of the circuit in ps.

        The result assumes that the circuit is implemented in a 130nm process, and that there is no
        setup or hold time associated with the circuit.  The resulting value is in picoseconds.  If
        an proper estimation of timing is required it is recommended to us "max_freq" to determine
        the clock period as it more accurately considers scaling and setup/hold.
        """
        return max(self.timing_map.values())

    def print_max_length(self):
        """Prints the max timing delay of the circuit """
        print("The total block timing delay is ", self.max_length())

    class _TooManyCPsError(Exception):
        pass

    def critical_path(self, print_cp=True, cp_limit=100):
        """ Takes a timing map and returns the critical paths of the system.

        :param print_cp: Whether to print the critical path to the terminal
            after calculation
        :return: a list containing tuples with the 'first' wire as the
            first value and the critical paths (which themselves are lists
            of nets) as the second
        """
        critical_paths = []  # storage of all completed critical paths
        wire_src_map, dst_map = self.block.net_connections()

        def critical_path_pass(old_critical_path, first_wire):
            if isinstance(first_wire, (Input, Const, Register)):
                critical_paths.append((first_wire, old_critical_path))
                return

            if len(critical_paths) >= cp_limit:
                raise self._TooManyCPsError()

            source = wire_src_map[first_wire]
            critical_path = [source]
            critical_path.extend(old_critical_path)
            arg_max_time = max(self.timing_map[arg_wire] for arg_wire in source.args)
            for arg_wire in source.args:
                # if the time for both items are the max, both will be on a critical path
                if self.timing_map[arg_wire] == arg_max_time:
                    critical_path_pass(critical_path, arg_wire)

        max_time = self.max_length()
        try:
            for wire_pair in self.timing_map.items():
                if wire_pair[1] == max_time:
                    critical_path_pass([], wire_pair[0])
        except self._TooManyCPsError:
            print("Critical path count limit reached")

        if print_cp:
            self.print_critical_paths(critical_paths)
        return critical_paths

    @staticmethod
    def print_critical_paths(critical_paths):
        """ Prints the results of the critical path length analysis.
            Done by default by the `TimingAnalysis().critical_path()` function.
        """
        line_indent = " " * 2
        #  print the critical path
        for cp_with_num in enumerate(critical_paths):
            print("Critical path", cp_with_num[0], ":")
            print(line_indent, "The first wire is:", cp_with_num[1][0])
            if _currently_in_jupyter_notebook():
                _print_netlist_latex(list(net for net in cp_with_num[1][1]))
            else:
                for net in cp_with_num[1][1]:
                    print(line_indent, (net))
            print()


# --------------------------------------------------------------------
#          __   __       __
#     \ / /  \ /__` \ / /__`
#      |  \__/ .__/  |  .__/
#

def yosys_area_delay(library, abc_cmd=None, leave_in_dir=None, block=None):
    """ Synthesize with Yosys and return estimate of area and delay.

    :param library: stdcell library file to target in liberty format
    :param abc_cmd: string of commands for yosys to pass to abc for synthesis
    :param dir: the directory where temporary files should be left
    :param block: pyrtl block to analyze
    :return: a tuple of numbers: area, delay

    If dir is specified, that directory will be used to create any temporary
    files, and the resulting files will be left behind there (which can be
    useful for manual exploration or debugging)

    The area and delay are returned in units as defined by the stdcell
    library.  In the standard vsc 130nm library, the area is in a number of
    "tracks", each of which is about 1.74 square um (see area estimation
    for more details) and the delay is in ps.

    http://www.vlsitechnology.org/html/vsc_description.html

    May raise `PyrtlError` if yosys is not configured correctly, and
    `PyrtlInternalError` if the call to yosys was not successful
    """

    if abc_cmd is None:
        abc_cmd = 'strash;scorr;ifraig;retime;dch,-f;map;print_stats;'
    else:
        # first, replace whitespace with commas as per yosys requirements
        re.sub(r"\s+", ',', abc_cmd)
        # then append with "print_stats" to generate the area and delay info
        abc_cmd = '%s;print_stats;' % abc_cmd

    def extract_area_delay_from_yosys_output(yosys_output):
        report_lines = [line
                        for line in yosys_output.decode().split('\n')
                        if 'ABC: netlist' in line]
        area = re.match(r'.*area\s*=\s*([0-9\.]*)', report_lines[0]).group(1)
        delay = re.match(r'.*delay\s*=\s*([0-9\.]*)', report_lines[0]).group(1)
        return float(area), float(delay)

    yosys_arg_template = """-p
    read_verilog %s;
    synth -top toplevel;
    dfflibmap -liberty %s;
    abc -liberty %s -script +%s
    """.replace('\n', ' ')

    temp_d, temp_path = tempfile.mkstemp(prefix='pyrtl_verilog', suffix='.v',
                                         dir=leave_in_dir, text=True)
    try:
        # write the verilog to a temp
        yosys_arg = yosys_arg_template % (temp_path, library, library, abc_cmd)
        with open(temp_path, 'w') as f:
            print('// generated via pyrtl yosys_area_delay', file=f)
            print('// yosys %s' % yosys_arg, file=f)
            output_to_verilog(f, block=block)
        os.close(temp_d)
        # call yosys on the temp, and grab the output
        yosys_output = subprocess.check_output(['yosys', yosys_arg])
        area, delay = extract_area_delay_from_yosys_output(yosys_output)
    except (subprocess.CalledProcessError, ValueError) as e:
        print('Error with call to yosys...', file=sys.stderr)
        print('---------------------------------------------', file=sys.stderr)
        print(str(e.output).replace('\\n', '\n'), file=sys.stderr)
        print('---------------------------------------------', file=sys.stderr)
        raise PyrtlError('Yosys callfailed')
    except OSError as e:
        print('Error with call to yosys...', file=sys.stderr)
        raise PyrtlError('Call to yosys failed (not installed or on path?)')
    finally:
        if leave_in_dir is None:
            os.remove(temp_path)
    return area, delay


def paths(src=None, dst=None, dst_nets=None, block=None):
    """ Get the list of paths from src to dst.

    :param WireVector src: source wire(s) from which to trace your paths;
        if None, will get paths from all Inputs
    :param WireVector dst: destination wire(s) to which to trace your paths
        if None, will get paths to all Outputs
    :param {WireVector: {LogicNet}} dst_nets: map from wire to set of nets where the
        wire is an argument; will compute it internally if not given via a
        call to pyrtl.net_connections()
    :param Block block: block to use (defaults to working block)
    :return: a map of the form {src_wire: {dst_wire: [path]}} for each src_wire in src
        (or all inputs if src is None), dst_wire in dst (or all outputs if dst is None),
        where path is a list of nets

    You can provide dst_nets (the result of calling pyrtl.net_connections()), if you plan
    on calling this function repeatedly on a block that hasn't changed, to speed things up.

    This function can accept one or more src wires, and one or more dst wires,
    such that it returns a map that can be accessed like so:

        paths[src][dst] = [<path>, <path>, ...]

    where <path> is a list of nets. Thus there can be multiple paths from a given src wire
    to a given dst wire.

    If src and dst are both single wires, you still need to access the result via paths[src][dst].
    """
    block = working_block(block)

    if dst_nets is None:
        # Note: if you set `include_virtual_nodes=True`, Output wires will actually
        # be present as the destination "net" of Output wires in the dst_nets map.
        # That would overly complicate this algorithm: we will assume all values()
        # in the dst_nets map are logic nets only. We set this to False for explicitness...
        _, dst_nets = block.net_connections(include_virtual_nodes=False)
    else:
        # ... or make sure it's not present otherwise.
        for output in block.wirevector_subset(cls=Output):
            dst_nets.pop(output, None)

    src = block.wirevector_subset(cls=Input) if src is None else {src}
    dst = block.wirevector_subset(cls=Output) if dst is None else {dst}

    def paths_src_dst(src, dst, block=None):
        paths = []

        # Use DFS to get the paths [each a list of nets] from src wire to dst wire
        def dfs(w, curr_path):
            if w is dst:
                # Found valid path
                paths.append(curr_path)
            for dst_net in dst_nets.get(w, []):
                # Avoid loops and the mem net (has no output wire)
                if (dst_net not in curr_path) and (dst_net.op != '@'):
                    dfs(dst_net.dests[0], curr_path + [dst_net])
        dfs(src, [])
        return paths

    all_paths = collections.defaultdict(dict)
    for src_wire in src:
        for dst_wire in dst:
            all_paths[src_wire][dst_wire] = paths_src_dst(src_wire, dst_wire)

    return all_paths


def distance(src, dst, f, block=None):
    """ Calculate the 'distance' along each path from src to dst according to f

    :param WireVector src: wire to start from
    :param WireVector dst: wire to end on
    :param (LogicNet -> Int) f: function from a net to number,
        representing the 'value' of a net that you want to sum
        across all nets in the path
    :param Block block: block to use (defaults to working block)
    :return: a map from each path (a tuple) to its calculated distance

    This calls the given function f on each net in a path, summing the result.
    """
    ps = paths(src, dst, block=block)
    ps = ps[src][dst]
    # Turning path into tuple so it can be the key
    m = {tuple(path): sum(map(f, path)) for path in ps}
    return m


def fanout(w):
    """ Get the number of places a wire is used as an argument.

    :param w: WireVector to check fanout for
    :return: integer fanout count
    """
    _, dst_nets = w._block.net_connections()
    if w not in dst_nets:
        return 0

    all_args = [arg for net in dst_nets[w] for arg in net.args]
    return len(list(filter(lambda arg: arg is w, all_args)))
