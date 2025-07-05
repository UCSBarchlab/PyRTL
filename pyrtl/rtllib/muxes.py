"""
Basic multiplexers are defined in PyRTL's core library, see:

- :func:`.select` for a multiplexer that selects between two options.

- :func:`.mux` for a multiplexer that selects between an arbitrary number of options.

- :ref:`conditional_assignment` for a more readable alternative to nested
  :func:`selects<.select>` and :func:`muxes<.mux>`.

The functions below provide more complex alternatives.
"""

import numbers

import pyrtl
from pyrtl import WireVector


def prioritized_mux(selects: list[WireVector], vals: list[WireVector]) -> WireVector:
    """Returns the value in the first wire for which its ``select`` bit is ``1``

    If none of the ``selects`` are ``1``, the last ``val`` is returned.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> selects = [pyrtl.Input(name=f"select{i}", bitwidth=1)
        ...            for i in range(3)]
        >>> vals = [pyrtl.Const(n) for n in range(2, 5)]
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.muxes.prioritized_mux(selects, vals)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"select0": 1, "select1": 0, "select2": 0})
        >>> sim.inspect("output")
        2

        >>> sim.step(provided_inputs={"select0": 0, "select1": 1, "select2": 0})
        >>> sim.inspect("output")
        3

        >>> sim.step(provided_inputs={"select0": 0, "select1": 0, "select2": 0})
        >>> sim.inspect("output")
        4

    :param selects: A list of :class:`WireVectors<.WireVector>` signaling whether a wire
        should be chosen.
    :param vals: Values to return when the corresponding ``select`` value is ``1``.

    :return: The selected value.
    """
    if len(selects) != len(vals):
        msg = "Number of select and val signals must match"
        raise pyrtl.PyrtlError(msg)
    if len(vals) == 0:
        msg = "Must have a signal to mux"
        raise pyrtl.PyrtlError(msg)
    if len(vals) == 1:
        return vals[0]
    half = len(vals) // 2
    return pyrtl.select(
        pyrtl.rtl_any(*selects[:half]),
        truecase=prioritized_mux(selects[:half], vals[:half]),
        falsecase=prioritized_mux(selects[half:], vals[half:]),
    )


def _is_equivalent(w1, w2):
    if isinstance(w1, pyrtl.Const) & isinstance(w2, pyrtl.Const):
        return (w1.val == w2.val) & (w1.bitwidth == w2.bitwidth)
    return w1 is w2


SparseDefault = "default"
"""
A special key for :func:`sparse_mux`'s ``vals`` :class:`dict` that specifies the mux's
default value.
"""


def sparse_mux(sel: WireVector, vals: dict[int, WireVector]) -> WireVector:
    """Mux that avoids instantiating unnecessary ``mux_2s`` when possible.

    ``sparse_mux`` supports not having a full specification. Indices that are not
    specified are treated as don't-cares.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> select = pyrtl.Input(name="select", bitwidth=3)
        >>> vals = {2: pyrtl.Const(3),
        ...         4: pyrtl.Const(5),
        ...         pyrtl.rtllib.muxes.SparseDefault: pyrtl.Const(7)}
        >>> output = pyrtl.Output(name="output")

        >>> output <<= pyrtl.rtllib.muxes.sparse_mux(select, vals)

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={"select": 2})
        >>> sim.inspect("output")
        3

        >>> sim.step(provided_inputs={"select": 4})
        >>> sim.inspect("output")
        5

        >>> sim.step(provided_inputs={"select": 3})
        >>> sim.inspect("output")
        7

    :param sel: Select wire, which chooses one of the mux input ``vals`` to output.
    :param vals: :class:`dict` of mux input values. If the special key
        :data:`SparseDefault` exists, it specifies the ``sparse_mux``'s default value.

    :return: The :class:`.WireVector` selected from ``vals`` by ``sel``.
    """
    max_val = 2 ** len(sel) - 1
    if SparseDefault in vals:
        default_val = vals[SparseDefault]
        del vals[SparseDefault]
        for i in range(max_val + 1):
            if i not in vals:
                vals[i] = default_val

    for key in vals:
        if not isinstance(key, numbers.Integral):
            msg = f"value {key} must be either an integer or 'default'"
            raise pyrtl.PyrtlError(msg)
        if key < 0 or key > max_val:
            msg = f"value {key} is out of range of the sel wire"
            raise pyrtl.PyrtlError(msg)

    return _sparse_mux(sel, vals)


def _sparse_mux(sel, vals):
    """Mux that avoids instantiating unnecessary mux_2s when possible.

    This mux supports not having a full specification. indices that are not specified
    are treated as Don't Cares

    :param WireVector sel: Select wire, determines what is selected on a given cycle
    :param {int: WireVector} vals: dictionary to store the values that are

    :return: WireVector that signifies the change
    """
    items = list(vals.values())
    if len(vals) <= 1:
        if len(vals) == 0:
            msg = "Needs at least one parameter for val"
            raise pyrtl.PyrtlError(msg)
        return items[0]

    if len(sel) == 1:
        try:
            false_result = vals[0]
            true_result = vals[1]
        except KeyError as exc:
            msg = (
                "Failed to retrieve values for smartmux. The length of sel might be "
                "wrong"
            )
            raise pyrtl.PyrtlError(msg) from exc
    else:
        half = 2 ** (len(sel) - 1)

        first_dict = {indx: wire for indx, wire in vals.items() if indx < half}
        second_dict = {indx - half: wire for indx, wire in vals.items() if indx >= half}
        if not first_dict:
            return sparse_mux(sel[:-1], second_dict)
        if not second_dict:
            return sparse_mux(sel[:-1], first_dict)

        false_result = sparse_mux(sel[:-1], first_dict)
        true_result = sparse_mux(sel[:-1], second_dict)
    if _is_equivalent(false_result, true_result):
        return true_result
    return pyrtl.select(sel[-1], falsecase=false_result, truecase=true_result)


class MultiSelector:
    """The MultiSelector allows you to specify multiple wire value results for a single
    select wire.

    Useful for processors, finite state machines and other places where the result of
    many wire values are determined by a common wire signal (such as a 'state' wire).

    Example::

        with muxes.MultiSelector(select, res0, res1, res2, ...) as ms:
            ms.option(val1, data0, data1, data2, ...)
            ms.option(val2, data0_2, data1_2, data2_2, ...)

    This means that when the ``select`` wire equals the ``val1`` wire the results will
    have the values in ``data0, data1, data2, ...`` (all ints are converted to wires)

    .. WARNING::

        Use :ref:`conditional_assignment` instead.
    """

    def __init__(self, signal_wire, *dest_wires):
        self._final = False
        self.dest_wires = dest_wires
        self.signal_wire = signal_wire
        self.instructions = []
        self.dest_instrs_info = {dest_w: [] for dest_w in dest_wires}

    def __enter__(self):
        """For compatibility with `with` statements, which is the recommended method of
        using a MultiSelector.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.finalize()
        else:
            print("The MultiSelector was not finalized due to uncaught exception")

    def _check_finalized(self):
        if self._final:
            msg = "Cannot change InstrConnector, already finalized"
            raise pyrtl.PyrtlError(msg)

    def option(self, select_val, *data_signals):
        self._check_finalized()
        instr, ib = pyrtl.infer_val_and_bitwidth(select_val, self.signal_wire.bitwidth)
        if instr in self.instructions:
            msg = f"instruction {select_val} already exists"
            raise pyrtl.PyrtlError(msg)
        self.instructions.append(instr)
        self._add_signal(data_signals)

    def default(self, *data_signals):
        self._check_finalized()
        self.instructions.append(SparseDefault)
        self._add_signal(data_signals)

    def _add_signal(self, data_signals):
        self._check_finalized()
        if len(data_signals) != len(self.dest_wires):
            msg = (
                "Incorrect number of data_signals for instruction received "
                f"{len(data_signals)}, expected {len(self.dest_wires)}"
            )
            raise pyrtl.PyrtlError(msg)

        for dw, sig in zip(self.dest_wires, data_signals):
            data_signal = pyrtl.as_wires(sig, dw.bitwidth)
            self.dest_instrs_info[dw].append(data_signal)

    def finalize(self):
        """Connects the wires."""
        self._check_finalized()
        self._final = True

        for dest_w, values in self.dest_instrs_info.items():
            mux_vals = dict(zip(self.instructions, values))
            dest_w <<= sparse_mux(self.signal_wire, mux_vals)


def demux(select: WireVector) -> tuple[WireVector, ...]:
    """Demultiplexes a wire of arbitrary bitwidth.

    This effectively converts an unsigned binary value into a one-hot encoded value,
    returning each bit of the one-hot encoded value as a separate :class:`.WireVector`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    Example::

        >>> input = pyrtl.Input(bitwidth=3)

        >>> outputs = pyrtl.rtllib.muxes.demux(input)
        >>> len(outputs)
        8
        >>> len(outputs[0])
        1
        >>> for i, wire in enumerate(outputs):
        ...     wire.name = f"outputs[{i}]"

        >>> sim = pyrtl.Simulation()
        >>> sim.step(provided_inputs={input.name: 5})

        >>> sim.inspect("outputs[4]")
        0
        >>> sim.inspect("outputs[5]")
        1
        >>> sim.inspect("outputs[6]")
        0

    In the example above, ``len(outputs)`` is ``8`` because ``2 ** 3 == 8``, and
    ``outputs[5]`` is ``1`` because the output index ``5`` matches the input value.

    See :func:`.binary_to_one_hot`, which performs a similar operation.

    .. WARNING::

        ``demux`` can create a very large number of ``WireVectors``. Use with
        caution.

    :param select: The value to demultiplex.

    :return: A tuple of 1-bit wires, where each wire indicates if the value of
             ``select`` equals the wire's index in the tuple. The tuple has length ``2
             ** select.bitwidth``.
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
    assert len(select) == 1
    return ~select, select
