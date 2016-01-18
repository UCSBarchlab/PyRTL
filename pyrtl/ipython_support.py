"""
ipython has a set of helperfunctions for running under ipython/jupyter.
"""

from __future__ import print_function, unicode_literals
from .pyrtlexceptions import PyrtlError, PyrtlInternalError
from .core import working_block


def _currently_in_ipython():
    """ Return true if running under ipython, otherwise return Fasle. """
    try:
        __IPYTHON__  # pylint: disable=undefined-variable
        return True
    except NameError:
        return False


