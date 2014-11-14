Hardware implementation of the H-Machine in pyrtl.

Main machine components:
Local registers, written only by hardware
Dual argument register band (read and write regs for each scope) with implicit switching
Evaluation stack and pointer
Text memory
Heap and heap pointer
Hardware GC (not yet designed...)
Stateful registers, including:
-execution pointer
-current environment closure
-number of locals in this scope so far
-number of arguments written so far
-maybe just the entire info table for this closure
