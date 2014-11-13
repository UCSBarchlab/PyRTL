""" Example 5: Making use of PyRTL and Introspection. """

import sys
sys.path.append("..")

import pyrtl

# The following example shows how pyrtl can be used to make some interesting
# hardware structures using python introspection.  In particular, this example
# makes a N-stage pipeline structure.

class SimplePipeline(object):
    """ Pipeline builder with auto generation of pipeline registers. """

    def __init__(self):
        self._pipeline_register_map = {}
        self._current_stage_num = 0
        stage_list = sorted(
            [method for
             method in dir(self)
             if method.startswith('stage')])
        for stage in stage_list:
            stage_method = getattr(self, stage)
            stage_method()
            self._current_stage_num += 1

    def __getattr__(self, name):
            try:
                return self._pipeline_register_map[self._current_stage_num][name]
            except KeyError:
                raise PyrtlError('error, no pipeline register "%s" defined for stage %d'
                                 % (name, self._current_stage_num))

    def __setattr__(self, name, value):
        if name.startswith('_'):
            # do not do anything tricky with variables starting with '_'
            object.__setattr__(self, name, value)
        else:
            rtype = appropriate_register_type(value)
            next_stage = self._current_stage_num + 1
            pipereg_id = str(self._current_stage_num) + 'to' + str(next_stage)
            rname = 'pipereg_' + pipereg_id + '_' + name
            new_pipereg = rtype(bitwidth=len(value), name=rname)
            if next_stage not in self._pipeline_register_map:
                self._pipeline_register_map[next_stage] = {}
            self._pipeline_register_map[next_stage][name] = new_pipereg
            new_pipereg.next <<= value


class SimplePipelineExample(SimplePipeline):
    """ A very simple pipeline to show how registers are inferred. """

    def __init__(self):
        self._loopback = WireVector(1, 'loopback')
        super(SimplePipelineExample, self).__init__()

    def stage0(self):
        self.n = ~ self._loopback

    def stage1(self):
        self.n = self.n

    def stage2(self):
        self.n = self.n

    def stage3(self):
        self.n = self.n

    def stage4(self):
        self._loopback <<= self.n


# Simulation of the core
sim_trace = SimulationTrace()
sim = Simulation(tracer=sim_trace)
for i in xrange(15):
    sim.step({})
sim_trace.render_trace()
