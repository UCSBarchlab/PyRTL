All FIRRTL related codes are in this `firrtl_tests` dir.

## Environment set up

Required tools:

- PyRTL and [FIRRTL](https://github.com/freechipsproject/firrtl)
- [firrtl-interpreter](https://github.com/freechipsproject/firrtl-interpreter)
- (please let me know if you have trouble setting up, I may have forgotten about some dependencies)


## To run the tests in firrtl-interpreter

- To translate PyRTL working block into FIRRTL code, call:

`translate_to_firrtl(working_block, output_file, rom_blocks=None)` 

- To generate test for the FIRRTL code and run in firrtl-interpreter, call:

`wrap_firrtl_test(sim_trace, working_block, firrtl_str, test_name, firrtl_test_path)`

and substitute the path with your own firrtl-interpreter path

- To run a single test in firrtl-interpreter

`sbt testOnly firrtl-interpreter.<testname>`



## Functions explanation in file `toFirrtl_new.py`

`translate_to_firrtl(working_block, output_file, rom_blocks=None)` 

will take args: a PyRTL working_block, an output file destination, and rom_blocks (if any), and generate FIRRTL codes into the output file. 

`generate_firrtl_test(sim_trace, working_block)` 

will generate test statements in scala. Each PyRTL simulation input and output will be mapped to a statement in scala, for example, an input named "a" that has simulation value 0,1,0,1 (per cycle) will generate the scala statement "val a = List(0,1,0,1)". Then each input and output will be tested using methods "poke" and "expect"

`wrap_firrtl_test(sim_trace, working_block, firrtl_str, test_name)` 

will wrap around the test statements. Combing with the translated `firrtl_string`, will generate a test file that can be tested in [firrtl-interpreter](https://github.com/freechipsproject/firrtl-interpreter). The test file should be written into `firrtl-interpreter/src/test/scala/firrtl_interpreter/`


## Other useful tools

### Compile some firrtl codes to lofirrtl form

in firrtl directory

- `./utils/bin/firrtl -tn ~/Desktop/mem.fir -X low`
