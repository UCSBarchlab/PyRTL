All FIRRTL related codes are in this `firrtl_tests` dir.

## Functions explanation

In file `toFirrtl_new.py`, function `translate_to_firrtl(block, firrtl_file, rom_blocks=None)` will take args: a PyRTL working_block, an output file destination, and rom_blocks (if any), and generate FIRRTL codes into the output file. Functions `generate_firrtl_test` and `wrap_firrtl_test` will generate a test file that can be tested in [firrtl-interpreter](https://github.com/freechipsproject/firrtl-interpreter). The test file should be written into `firrtl-interpreter/src/test/scala/firrtl_interpreter/`

## Environment set up

Required tools:

- PyRTL and [FIRRTL](https://github.com/freechipsproject/firrtl)
- [firrtl-interpreter](https://github.com/freechipsproject/firrtl-interpreter)
- (please let me know if you have trouble setting up, I may have forgotten about some dependencies)

## To run the tests in firrtl-interpreter

need to modify some path name

- in function `wrap_firrtl_test`, substitute the path with your own firrtl-interpreter path

To run a single test

- `sbt testOnly firrtl-interpreter.<testname>`

## Compile some firrtl codes to lofirrtl form

in firrtl directory

- `./utils/bin/firrtl -tn ~/Desktop/mem.fir -X low`
