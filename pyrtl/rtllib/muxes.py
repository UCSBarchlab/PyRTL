import pyrtl


def prioritized_mux(selects, vals):
    """ Returns the value in the first wire for which its select bit is 1

    :param [WireVector] selects: a list of WireVectors signaling whether
        a wire should be chosen
    :param [WireVector] vals: values to return when the corresponding select
        value is 1
    :return: WireVector

    If none of the items are high, the last val is returned
    """
    if len(selects) != len(vals):
        raise pyrtl.PyrtlError("Number of select and val signals must match")
    if len(vals) == 0:
        raise pyrtl.PyrtlError("Must have a signal to mux")
    if len(vals) == 1:
        return vals[0]
    else:
        half = len(vals) // 2
        return pyrtl.select(pyrtl.rtl_any(*selects[:half]),
                            truecase=prioritized_mux(selects[:half], vals[:half]),
                            falsecase=prioritized_mux(selects[half:], vals[half:]))


def _is_equivalent(w1, w2):
    if isinstance(w1, pyrtl.Const) & isinstance(w2, pyrtl.Const):
        return (w1.val == w2.val) & (w1.bitwidth == w2.bitwidth)
    return w1 is w2


SparseDefault = "default"


def sparse_mux(sel, vals):
    """ Mux that avoids instantiating unnecessary mux_2s when possible.

    :param WireVector sel: Select wire, determines what is selected on a given cycle
    :param dictionary vals: dictionary of values at mux inputs (of type `{int:WireVector}`)
    :return: WireVector that signifies the change

    This mux supports not having a full specification. Indices that are not
    specified are treated as don't-cares

    It also supports a specified default value, SparseDefault
    """
    import numbers

    max_val = 2**len(sel) - 1
    if SparseDefault in vals:
        default_val = vals[SparseDefault]
        del vals[SparseDefault]
        for i in range(max_val + 1):
            if i not in vals:
                vals[i] = default_val

    for key in vals.keys():
        if not isinstance(key, numbers.Integral):
            raise pyrtl.PyrtlError("value %s nust be either an integer or 'default'" % str(key))
        if key < 0 or key > max_val:
            raise pyrtl.PyrtlError("value %s is out of range of the sel wire" % str(key))

    return _sparse_mux(sel, vals)


def _sparse_mux(sel, vals):
    """ Mux that avoids instantiating unnecessary mux_2s when possible.

    :param WireVector sel: Select wire, determines what is selected on a given cycle
    :param {int: WireVector} vals: dictionary to store the values that are
    :return: Wirevector that signifies the change

    This mux supports not having a full specification. indices that are not
    specified are treated as Don't Cares
    """
    items = list(vals.values())
    if len(vals) <= 1:
        if len(vals) == 0:
            raise pyrtl.PyrtlError("Needs at least one parameter for val")
        return items[0]

    if len(sel) == 1:
        try:
            false_result = vals[0]
            true_result = vals[1]
        except KeyError:
            raise pyrtl.PyrtlError("Failed to retrieve values for smartmux. "
                                   "The length of sel might be wrong")
    else:
        half = 2**(len(sel) - 1)

        first_dict = {indx: wire for indx, wire in vals.items() if indx < half}
        second_dict = {indx - half: wire for indx, wire in vals.items() if indx >= half}
        if not len(first_dict):
            return sparse_mux(sel[:-1], second_dict)
        if not len(second_dict):
            return sparse_mux(sel[:-1], first_dict)

        false_result = sparse_mux(sel[:-1], first_dict)
        true_result = sparse_mux(sel[:-1], second_dict)
    if _is_equivalent(false_result, true_result):
        return true_result
    return pyrtl.select(sel[-1], falsecase=false_result, truecase=true_result)


class MultiSelector(object):
    """ The MultiSelector allows you to specify multiple wire value results
    for a single select wire.

    Useful for processors, finite state machines and other places where the
    result of many wire values are determined by a common wire signal
    (such as a 'state' wire).

    Example::

        with muxes.MultiSelector(select, res0, res1, res2, ...) as ms:
            ms.option(val1, data0, data1, data2, ...)
            ms.option(val2, data0_2, data1_2, data2_2, ...)

    This means that when the select wire equals the val1 wire
    the results will have the values in the coresponding data wires
    (all ints are converted to wires)
    """
    def __init__(self, signal_wire, *dest_wires):
        self._final = False
        self.dest_wires = dest_wires
        self.signal_wire = signal_wire
        self.instructions = []
        self.dest_instrs_info = {dest_w: [] for dest_w in dest_wires}

    def __enter__(self):
        """ For compatibility with `with` statements, which is the recommended
        method of using a MultiSelector.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.finalize()
        else:
            print("The MultiSelector was not finalized due to uncaught exception")

    def _check_finalized(self):
        if self._final:
            raise pyrtl.PyrtlError("Cannot change InstrConnector, already finalized")

    def option(self, select_val, *data_signals):
        self._check_finalized()
        instr, ib = pyrtl.infer_val_and_bitwidth(select_val, self.signal_wire.bitwidth)
        if instr in self.instructions:
            raise pyrtl.PyrtlError("instruction %s already exists" % str(select_val))
        self.instructions.append(instr)
        self._add_signal(data_signals)

    def default(self, *data_signals):
        self._check_finalized()
        self.instructions.append(SparseDefault)
        self._add_signal(data_signals)

    def _add_signal(self, data_signals):
        self._check_finalized()
        if len(data_signals) != len(self.dest_wires):
            raise pyrtl.PyrtlError("Incorrect number of data_signals for "
                                   "instruction received {} , expected {}"
                                   .format(len(data_signals), len(self.dest_wires)))

        for dw, sig in zip(self.dest_wires, data_signals):
            data_signal = pyrtl.as_wires(sig, dw.bitwidth)
            self.dest_instrs_info[dw].append(data_signal)

    def finalize(self):
        """ Connects the wires.
        """
        self._check_finalized()
        self._final = True

        for dest_w, values in self.dest_instrs_info.items():
            mux_vals = dict(zip(self.instructions, values))
            dest_w <<= sparse_mux(self.signal_wire, mux_vals)


def demux(select):
    """ Demultiplexes a wire of arbitrary bitwidth

    :param WireVector select: indicates which wire to set on
    :return (WireVector, ...): a tuple of wires corresponding to each demultiplexed wire
    """
    if len(select) == 1:
        return _demux_2(select)

    wires = demux(select[:-1])
    sel = select[-1]
    not_select = ~sel
    zero_wires = tuple(not_select & w for w in wires)
    one_wires = tuple(sel & w for w in wires)
    return zero_wires + one_wires


def _demux_2(select):
    assert(len(select) == 1)
    return ~select, select
