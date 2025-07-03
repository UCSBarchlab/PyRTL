from __future__ import annotations

import random
from typing import Callable

import pyrtl


def calculate_max_and_min_bitwidths(max_bitwidth=None, exact_bitwidth=None):
    if max_bitwidth is not None:
        min_bitwidth = 1
    elif exact_bitwidth is not None:
        min_bitwidth = max_bitwidth = exact_bitwidth
    else:
        msg = "A max or exact bitwidth must be specified"
        raise pyrtl.PyrtlError(msg)
    return min_bitwidth, max_bitwidth


def inverse_power_dist(bitwidth):
    # Note that this is not uniformly distributed
    return int(2 ** random.uniform(0, bitwidth) - 1)


def uniform_dist(bitwidth):
    return random.randrange(2**bitwidth)


def make_inputs_and_values(
    num_wires: int,
    max_bitwidth: int | None = None,
    exact_bitwidth: int | None = None,
    dist: Callable[[int], int] = uniform_dist,
    test_vals: int = 20,
) -> tuple[list[pyrtl.Input], list[list[int]]]:
    """Generates multiple :class:`.Input` wires and their test values.

    The generated list of test values is a list of lists. The inner lists each represent
    the values of a single :class:`.Input` wire, for each :class:`.Simulation` cycle.

    :param num_wires: Number of :class:`Inputs<.Input>` to generate.
    :param max_bitwidth: If specified, generate :class:`Inputs<.Input>` with random
        :attr:`~.WireVector.bitwidth` in the range ``[1, max_bitwidth)``.
    :param exact_bitwidth: If specified, generate :class:`Inputs<.Input>` with
        :attr:`~.WireVector.bitwidth` ``exact_bitwidth``.
    :param dist: Function to generate the random :class:`.Input` values.
    :param test_vals: Number of random :class:`.Input` values to generate.

    :return: ``(inputs, values)``, where ``inputs`` is a :class:`list` of
             :class:`Inputs<.Input>`, and ``values`` is a list of values for each
             ``input``.
    """
    min_bitwidth, max_bitwidth = calculate_max_and_min_bitwidths(
        max_bitwidth, exact_bitwidth
    )
    wires, vals = list(
        zip(
            *(
                an_input_and_vals(
                    random.randrange(min_bitwidth, max_bitwidth + 1),
                    test_vals,
                    random_dist=dist,
                )
                for i in range(num_wires)
            )
        )
    )
    return wires, vals


def an_input_and_vals(
    bitwidth: int,
    test_vals: int = 20,
    name: str = "",
    random_dist: Callable[[int], int] = uniform_dist,
) -> tuple[pyrtl.Input, list[int]]:
    """Generate an :class:`.Input` wire and random test values for it.

    :param bitwidth: The bitwidth of the random values to generate.
    :param test_vals: Number of random values to generate per :class:`.Input`.
    :param name: Name of the returned :class:`.Input`.

    :return: ``(input_wire, test_values)``, where ``input_wire`` is an :class:`.Input`,
             and ``test_values`` is a list of random test values for ``input_wire``.
    """
    input_wire = pyrtl.Input(bitwidth, name=name)  # Creating a new input wire
    test_vals = [random_dist(bitwidth) for i in range(test_vals)]
    return input_wire, test_vals


# deprecated name
generate_in_wire_and_values = an_input_and_vals


def make_consts(
    num_wires: int,
    max_bitwidth: int | None = None,
    exact_bitwidth: int | None = None,
    random_dist: Callable[[int], int] = inverse_power_dist,
) -> tuple[list[pyrtl.Const], list[int]]:
    """Generate random :class:`.Const` values.

    :param num_wires: Number of :class:`Consts<.Const>` to generate.
    :param max_bitwidth: If specified, generate :class:`Consts<.Const>` with random
        :attr:`~.WireVector.bitwidth` in the range ``[1, max_bitwidth)``.
    :param exact_bitwidth: If specified, generate :class:`Consts<.Const>` with
        :attr:`~.WireVector.bitwidth` ``exact_bitwidth``.
    :param random_dist: Function to generate the random :class:`.Const` values.

    :return: ``(consts, values)``, where ``consts`` is a :class:`list` of
             :class:`Consts<.Const>`, and ``values`` is a list of each ``const``'s
             value.
    """
    min_bitwidth, max_bitwidth = calculate_max_and_min_bitwidths(
        max_bitwidth, exact_bitwidth
    )
    bitwidths = [
        random.randrange(min_bitwidth, max_bitwidth + 1) for i in range(num_wires)
    ]
    wires = [pyrtl.Const(random_dist(b), b) for b in bitwidths]
    vals = [w.val for w in wires]
    return wires, vals


def sim_and_ret_out(
    outwire: pyrtl.WireVector, inwires: list[pyrtl.WireVector], invals: list[list[int]]
) -> list[int]:
    """Run a simulation with ``invals`` for ``inwires`` and return ``outwire``'s values.

    .. WARNING::

        Use :meth:`.Simulation.step_multiple` instead::

            sim = pyrtl.Simulation()
            sim.step_multiple(provided_inputs=dict(zip(inwires, invals)))
            output = sim.tracer.trace[outwire.name]

    :param outwire: The wire to return the values of in each simulation cycle.
    :param inwires: A list of :class:`.Input` wires to provide values for.
    :param invals: A list of :class:`.Input` value lists.

    :return: A list of ``outwire``'s values in each simulation cycle.
    """
    # Pulling the value of outwire straight from the log
    return sim_and_ret_outws(inwires, invals)[outwire.name]


def sim_and_ret_outws(
    inwires: list[pyrtl.WireVector], invals: list[list[int]]
) -> dict[str, list[int]]:
    """Run a simulation with ``invals`` for ``inwires`` and return all wire values.

    .. WARNING::

        Use :meth:`.Simulation.step_multiple` instead::

            sim = pyrtl.Simulation()
            sim.step_multiple(provided_inputs=dict(zip(inwires, invals)))
            outputs = sim.tracer.trace

    :param inwires: A list of :class:`.Input` wires to provide values for.
    :param invals: A list of :class:`.Input` value lists.

    :return: A :class:`dict` mapping from a :class:`WireVector`'s name to a
             :class:`list` of its values in each cycle.
    """
    sim = pyrtl.Simulation()
    sim.step_multiple(provided_inputs=dict(zip(inwires, invals)))
    return sim.tracer.trace


def sim_multicycle(in_dict, hold_dict, hold_cycles, sim=None):
    if sim is None:
        sim = pyrtl.Simulation()
    sim.step(in_dict)
    for _i in range(hold_cycles):
        sim.step(hold_dict)
    return sim.tracer.trace[-1]


def multi_sim_multicycle(in_dict, hold_dict, hold_cycles, sim=None):
    if sim is None:
        sim = pyrtl.Simulation()
    cycles = len(next(iter(in_dict.values())))
    for cycle in range(cycles):
        current_dict = {wire: values[cycle] for wire, values in in_dict}
        cur_result = sim_multicycle(current_dict, hold_dict, hold_cycles, sim)
        if cycle == 0:
            results = {wire: [result_val] for wire, result_val in cur_result}
        else:
            for wire, result_val in cur_result:
                results[wire].append(result_val)
    return results
