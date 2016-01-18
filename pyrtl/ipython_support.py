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


def render_trace_to_ipython(trace, sortkey, trace_list=None):
    """ Render a trace for viewing in IPython. """
    from IPython.display import display, HTML, Javascript  # pylint: disable=import-error

    def rle(trace):
        l = []
        last = ''
        for i in range(len(trace)):
            if last == trace[i]:
                l.append('.')
            else:
                l.append(str(trace[i]))
                last = trace[i]
        return ''.join(l)

    # default to printing all signals in sorted order
    if trace_list is None:
        trace_list = sorted(trace, key=sortkey)

    wave_template = (
        """\
        <script src="http://wavedrom.com/skins/default.js" type="text/javascript"></script>
        <script src="http://wavedrom.com/WaveDrom.js" type="text/javascript"></script>
        <script type="WaveDrom">
        { signal : [
        %s
        ]}
        </script>
        """
        )
    signal_template = '{ name: "%s",  wave: "%s" },'
    signals = [signal_template % (w.name, rle(trace[w])) for w in trace_list]
    all_signals = '\n'.join(signals)
    wave = wave_template % all_signals
    display(HTML(wave))
    display(Javascript('WaveDrom.ProcessAll()'))


# def render_logic_to_ipython(block=None, namer=_default_namer):
#    from IPython.display import display, HTML, Javascript  # pylint: disable=import-error
#    block = working_block(block)
#    graph = block.as_graph()
#    tree = _graph_to_logic_tree(graph)
#    logic_template = (
#        """\
#        <script type="WaveDrom">
#        { signal: []}
#        </script>
#        <script type="WaveDrom">
#        { assign:[
#        %s
#        ]}
#        </script>
#        """
#        )
#    s = _str_from_logic_tree(tree)
#    logicstr = logic_template % s
#    display(HTML(logicstr))
#    display(Javascript('WaveDrom.ProcessAll()'))
