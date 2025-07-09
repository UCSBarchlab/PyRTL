# # Example 5: Making use of PyRTL and Introspection.
import pyrtl


# The following example shows how PyRTL can be used to make some interesting hardware
# structures using Python introspection. In particular, this example makes a N-stage
# pipeline structure. Any specific pipeline is then a derived class of `SimplePipeline`
# where methods with names starting with `stage` are stages, and new members with names
# not starting with `_` are to be registered for the next stage.
#
# ## Pipeline builder with auto generation of pipeline registers.
class SimplePipeline:
    def __init__(self):
        self._pipeline_register_map = {}
        self._current_stage_num = 0
        stage_list = [method for method in dir(self) if method.startswith("stage")]
        for stage in sorted(stage_list):
            stage_method = getattr(self, stage)
            stage_method()
            self._current_stage_num += 1

    def __getattr__(self, name):
        try:
            return self._pipeline_register_map[self._current_stage_num][name]
        except KeyError as exc:
            msg = (
                f'error, no pipeline register "{name}" defined for stage '
                f"{self._current_stage_num}"
            )
            raise pyrtl.PyrtlError(msg) from exc

    def __setattr__(self, name, value):
        if name.startswith("_"):
            # do not do anything tricky with variables starting with '_'
            object.__setattr__(self, name, value)
        else:
            next_stage = self._current_stage_num + 1
            pipereg_id = f"{self._current_stage_num} to {next_stage}"
            rname = f"pipereg_{pipereg_id}_name"
            new_pipereg = pyrtl.Register(bitwidth=len(value), name=rname)
            if next_stage not in self._pipeline_register_map:
                self._pipeline_register_map[next_stage] = {}
            self._pipeline_register_map[next_stage][name] = new_pipereg
            new_pipereg.next <<= value


# ## A very simple pipeline to show how registers are inferred.
class SimplePipelineExample(SimplePipeline):
    def __init__(self):
        self._loopback = pyrtl.WireVector(1, "loopback")
        super().__init__()

    def stage0(self):
        self.n = ~self._loopback

    def stage1(self):
        self.n = self.n

    def stage2(self):
        self.n = self.n

    def stage3(self):
        self.n = self.n

    def stage4(self):
        self._loopback <<= self.n


simplepipeline = SimplePipelineExample()
print(pyrtl.working_block())
# ## Simulation of the core
sim = pyrtl.Simulation()
sim.step_multiple({}, nsteps=15)
sim.tracer.render_trace()
