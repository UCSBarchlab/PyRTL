""" Example 4: Debugging

Debugging is half the coding process in software, and in PyRTL, it's no
different. PyRTL provides some additional challenges when it comes to
debugging as a problem may surface long after the error was made. Fortunately,
PyRTL comes with various features to help you find mistakes.
"""

import sys
sys.path.append("..")
import pyrtl

# Firstly, we will assume that you have experience debugging code. If you do
# not, we recommend that you look at _________ to get yourself oriented with
# how to debug Python code.


# In this example, we will be building a circuit that adds up three values.
# However, instead of building an add function ourselves or using the
# built-in + function in PyRTL, we will instead use the Kogge-Stone adders
# in RtlLib, the standard library for PyRTL.

# The first step to use the RtlLib is to import it
from rtllib import adders

# building three inputs
in1, in2, in3 = (pyrtl.Input(8, "i" + str(x)) for x in range(1, 4))
out = pyrtl.Output(10, "out")

add1_out = adders.kogge_stone(in1, in2)
add2_out = adders.kogge_stone(add1_out, in2)
out <<= add2_out

exit(0)
# the rest of this example is not yet ready


# Finally, there is a handy way to view your hardware creations as a graph.  The function
# output_to_trivialgraph will render your hardware a formal that you can then open with the
# free software "yEd" (http://en.wikipedia.org/wiki/YEd).  There are options under the
# "heirachical" rendering to draw something looks quite like a circuit.

import io
print "--- Trivial Graph Format  ---"
with io.BytesIO() as tgf:
    pyrtl.output_to_trivialgraph(tgf)
    print tgf.getvalue()
