import unittest
import pyrtl
from random import randint


# -------------------------------------------------------------------
class RTLMemBlockDesignBase(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.addrwidth = 5
        self.output1 = pyrtl.Output(self.bitwidth, "output1")
        self.output2 = pyrtl.Output(self.bitwidth, "output2")
        self.mem_read_address1 = pyrtl.Input(self.addrwidth, name='mem_read_address1')
        self.mem_read_address2 = pyrtl.Input(self.addrwidth, name='mem_read_address2')
        self.mem_write_address = pyrtl.Input(self.addrwidth, name='mem_write_address')
        self.mem_write_data = pyrtl.Input(self.bitwidth, name='mem_write_data')
        self.memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                     name='self.memory', max_read_ports=None)

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_memblock_simple(self):
        self.output1 <<= self.memory[self.mem_read_address1]
        self.output2 <<= self.memory[self.mem_read_address2]
        self.memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check()

    def test_memblock_assign_with_extention(self):
        big_output = pyrtl.Output(self.bitwidth + 1, "big_output")
        big_output <<= self.memory[self.mem_read_address1]
        self.output1 <<= 1
        self.output2 <<= 2
        self.memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check()

    def test_memblock_with_write_enable_with_equalsign(self):
        we = pyrtl.Const(1, bitwidth=1)
        self.output1 <<= self.memory[self.mem_read_address1]
        self.output2 <<= self.memory[self.mem_read_address2]
        self.memory[self.mem_write_address] <<= \
            pyrtl.MemBlock.EnabledWrite(self.mem_write_data, enable=we)
        pyrtl.working_block().sanity_check()

    def test_memblock_direct_assignment_error(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.memory[self.mem_write_address] = self.mem_write_data

    def test_memblock_connection_with_ints(self):
        self.memory[self.mem_write_address] <<= 5

    # test does not check functionality, just that it will generate hardware
    def test_memblock_to_memblock_direct_operation(self):
        temp = (self.memory[self.mem_read_address1] == self.memory[self.mem_read_address2])
        temp = (self.memory[self.mem_read_address1] != self.memory[self.mem_read_address2])
        temp = (self.memory[self.mem_read_address1] & self.memory[self.mem_read_address2])
        temp = (self.memory[self.mem_read_address1] | self.memory[self.mem_read_address2])
        temp = (self.memory[self.mem_read_address1] + self.memory[self.mem_read_address2])
        temp = (self.memory[self.mem_read_address1] - self.memory[self.mem_read_address2])
        temp2 = (self.memory[self.mem_read_address1] * self.memory[self.mem_read_address2])
        self.output1 <<= temp
        self.output2 <<= temp2
        pyrtl.working_block().sanity_check()

    def test_2read_1write(self):
        small_memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                      name='small_memory', max_read_ports=2, max_write_ports=1)
        temp = small_memory[self.mem_read_address1]  # read
        temp2 = small_memory[self.mem_read_address2]  # read

        self.output1 <<= temp
        self.output2 <<= temp2
        small_memory[self.mem_write_address] <<= pyrtl.Const(6)  # write
        pyrtl.working_block().sanity_check()

    def test_over_max_read_ports(self):
        lim_memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                    name='lim_memory', max_read_ports=8)
        for i in range(lim_memory.max_read_ports):
            self.output1 <<= lim_memory[self.mem_read_address1]
        with self.assertRaises(pyrtl.PyrtlError):
            self.output2 <<= lim_memory[self.mem_read_address2]

    def test_over_max_write_ports(self):
        lim_memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                    name='lim_memory', max_write_ports=4)
        for i in range(lim_memory.max_write_ports):
            lim_memory[self.mem_write_address] <<= pyrtl.Const(6)
        with self.assertRaises(pyrtl.PyrtlError):
            lim_memory[self.mem_write_address] <<= pyrtl.Const(6)

    def test_memblock_added_user_named(self):
        mem_name = 'small_memory'
        small_memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                      name=mem_name, max_read_ports=2, max_write_ports=1)
        self.assertIs(pyrtl.working_block().get_memblock_by_name(mem_name), small_memory)

    def test_memblock_added_default_named(self):
        mem = pyrtl.MemBlock(32, 8)
        self.assertIs(pyrtl.working_block().get_memblock_by_name(mem.name), mem)


class MemIndexedTests(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_memindexed_name(self):
        self.mem = pyrtl.MemBlock(8, 8)
        x = self.mem[2]
        x.name = 'test_name'
        self.assertEquals(x.name, 'test_name')
        self.assertEquals(x.wire.name, 'test_name')

    def test_read_memindexed_ilshift(self):
        self.mem = pyrtl.MemBlock(8, 8)
        self.mem_val_map = {self.mem: {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 0}}
        a = pyrtl.Input(3)
        x = self.mem[a]
        y = pyrtl.Output(8, 'y')
        z = pyrtl.Output(8, 'z')
        y <<= x
        z <<= x
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map=self.mem_val_map)
        for i in range(5):
            sim.step({
                a: i
            })
            self.assertEqual(sim.inspect(y), 5 - i)
            self.assertEqual(sim.inspect(z), 5 - i)
        self.assertEqual(self.mem.num_read_ports, 1)

    def test_write_memindexed_ilshift(self):
        self.mem1 = pyrtl.MemBlock(8, 8)
        self.mem2 = pyrtl.MemBlock(8, 8, asynchronous=True)
        self.mem_val_map = {self.mem1: {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5}}
        addr1 = pyrtl.Input(3)
        addr2 = pyrtl.Input(3)  # will be one behind addr1
        inp = pyrtl.Input(3)
        x = self.mem1[addr1]  # value follows addr1
        self.mem2[x] <<= inp
        out = pyrtl.Output(9, name='out')
        out <<= self.mem2[addr2]  # one behind addr1, so one behind x
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map=self.mem_val_map)
        for i in range(5):
            sim.step({
                addr1: i,
                addr2: 0 if i == 0 else i - 1,  # one behind addr1
                inp: 5 - i
            })
            self.assertEqual(sim.inspect(out), 0 if i == 0 else 5 - (i - 1))
        self.assertEqual(self.mem1.num_read_ports, 1)  # 2 b/c of the output read
        self.assertEqual(self.mem2.num_write_ports, 1)

    def test_read_memindexed_ior(self):
        self.mem = pyrtl.MemBlock(8, 8)
        self.mem_val_map = {self.mem: {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 0}}
        decide = pyrtl.Input(1)
        ind = pyrtl.Input(3)
        x = self.mem[ind]
        y = pyrtl.Output(8, 'y')
        z = pyrtl.Output(8, 'z')
        w = pyrtl.Output(8, 'w')
        with pyrtl.conditional_assignment:
            with decide:
                y |= x
                z |= x
            with pyrtl.otherwise:
                w |= x
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map=self.mem_val_map)
        for i in range(5):
            sim.step({
                decide: i % 2,
                ind: i
            })
            if i == 0:
                y_exp, z_exp, w_exp = 0, 0, 5
            elif i == 1:
                y_exp, z_exp, w_exp = 4, 4, 0
            elif i == 2:
                y_exp, z_exp, w_exp = 0, 0, 3
            elif i == 3:
                y_exp, z_exp, w_exp = 2, 2, 0
            else:
                y_exp, z_exp, w_exp = 0, 0, 1
            self.assertEqual(sim.inspect(y), y_exp)
            self.assertEqual(sim.inspect(z), z_exp)
            self.assertEqual(sim.inspect(w), w_exp)
        self.assertEqual(self.mem.num_read_ports, 1)

    def test_write_memindexed_ior(self):
        self.mem1 = pyrtl.MemBlock(8, 8)
        self.mem2 = pyrtl.MemBlock(8, 8, asynchronous=True)
        self.mem_val_map = {self.mem1: {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5}}
        decide = pyrtl.Input(1)
        inp = pyrtl.Input(3)
        addr1 = pyrtl.Input(3)
        addr2 = pyrtl.Input(3)  # will be one behind addr1
        zero = pyrtl.Const(0, 3)
        x = self.mem1[addr1]
        x.name = 'x'
        out = pyrtl.Output(8, name='out')
        with pyrtl.conditional_assignment:
            with decide:
                self.mem2[x] |= inp
            with pyrtl.otherwise:
                self.mem2[x] |= zero
        out <<= self.mem2[addr2]  # one behind addr1, so one behind x
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map=self.mem_val_map)
        for i in range(5):
            sim.step({
                decide: i % 2,
                addr1: i,
                addr2: 0 if i == 0 else i - 1,  # one behind addr1
                inp: 5 - i
            })
            if (i == 0) | (i == 1) | (i == 3):
                out_exp = 0
            elif i == 2:
                out_exp = 4
            else:
                out_exp = 2
            self.assertEqual(sim.inspect(out), out_exp)
        self.assertEqual(self.mem1.num_read_ports, 1)
        self.assertEqual(self.mem2.num_write_ports, 1)


class RTLRomBlockWiring(unittest.TestCase):
    data = list(range(2**5))

    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.addrwidth = 5
        self.output1 = pyrtl.Output(self.bitwidth, "output1")
        self.in1 = pyrtl.Input(self.addrwidth, name='mem_write_address')
        self.in2 = pyrtl.Input(self.addrwidth, name='mem_write_address')
        self.memory = pyrtl.RomBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth,
                                     name='self.memory', romdata=self.data, max_read_ports=None)

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_read(self):
        self.output1 <<= self.memory[self.in1]

    def test_direct_assignment_error(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.memory[self.in1] = self.in2

    def test_int_index_error(self):
        with self.assertRaises(pyrtl.PyrtlError):
            x = self.memory[3]

    def test_other_non_wire_index_error(self):
        with self.assertRaises(pyrtl.PyrtlError):
            y = self.memory[()]
        with self.assertRaises(pyrtl.PyrtlError):
            y = self.memory["test"]
        with self.assertRaises(pyrtl.PyrtlError):
            y = self.memory["15"]
        with self.assertRaises(pyrtl.PyrtlError):
            y = self.memory[False]

    def test_write(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.memory[self.in1] <<= 5

    # test does not check functionality, just that it will generate hardware
    def test_rom_to_rom_direct_operation(self):
        temp = (self.memory[self.in1] == self.memory[self.in2])
        temp = (self.memory[self.in1] != self.memory[self.in2])  # != creates two nets
        temp = (self.memory[self.in1] & self.memory[self.in2])
        temp = (self.memory[self.in1] | self.memory[self.in2])
        temp = (self.memory[self.in1] + self.memory[self.in2])
        temp = (self.memory[self.in1] - self.memory[self.in2])
        temp = (self.memory[self.in1] * self.memory[self.in2])
        block = pyrtl.working_block()
        self.assertEqual(len(block.logic), 22)
        self.output1 <<= temp


class RTLRomGetReadData(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    @staticmethod
    def sample_roms():
        def rom_func(address):
            return (2 * address + 1) % 8
        rom = pyrtl.RomBlock(3, 3, [2, 4, 7, 1])
        romf = pyrtl.RomBlock(3, 3, rom_func)
        return rom, romf

    def invalid_rom_read(self, rom, address):
        with self.assertRaises(pyrtl.PyrtlError):
            rom._get_read_data(address)

    def test_invalid_address(self):
        for rom in self.sample_roms():
            self.invalid_rom_read(rom, -1)
            self.invalid_rom_read(rom, 8)
            self.invalid_rom_read(rom, 5809)

    def test_invalid_address_types(self):
        for rom in self.sample_roms():
            self.invalid_rom_read(rom, 'test')
            self.invalid_rom_read(rom, pyrtl.Const(10))
            self.invalid_rom_read(rom, [])
            self.invalid_rom_read(rom, slice(1, 3))
            # self.invalid_rom_read(rom, False)  # should this be valid?

    def test_invalid_value_function(self):
        def bad_func(address):
            return str(address)

        def bad_func_2(address):
            return pyrtl.Const(address)

        rom1 = pyrtl.RomBlock(5, 5, ['test', ()])
        rom2 = pyrtl.RomBlock(5, 5, [pyrtl.Const(0), bad_func])
        romf1 = pyrtl.RomBlock(5, 5, bad_func)
        romf2 = pyrtl.RomBlock(5, 5, bad_func_2)
        for rom in (rom1, rom2, romf1, romf2):
            self.invalid_rom_read(rom, 0)
            self.invalid_rom_read(rom, 1)

    def test_value_out_of_range(self):
        def rom_func(address):
            return 2 * (8 - address) + 1

        rom1 = pyrtl.RomBlock(3, 3, [15, 8, 7, 1])
        romf1 = pyrtl.RomBlock(3, 3, rom_func)

        for rom in (rom1, romf1):
            self.invalid_rom_read(rom, 0)
            self.invalid_rom_read(rom, 1)

    def test_out_of_range(self):
        for rom in self.sample_roms():
            self.invalid_rom_read(rom, -1)
            self.invalid_rom_read(rom, 8)
            self.invalid_rom_read(rom, 5809)

    def test_over_max_read_ports(self):
        width = 6
        rom = pyrtl.RomBlock(width, width, [2, 4, 7, 1])
        for i in range(rom.max_read_ports):
            rom_read_address = pyrtl.Input(width)
            rom_out = pyrtl.Output(width)
            rom_out <<= rom[rom_read_address]
        rom_read_address = pyrtl.Input(width)
        rom_out = pyrtl.Output(width)
        with self.assertRaises(pyrtl.PyrtlError):
            rom_out <<= rom[rom_read_address]

    def test_valid_get_read(self):
        rom, romf = self.sample_roms()
        for address, expected in enumerate((2, 4, 7, 1)):
            self.assertEqual(rom._get_read_data(address), expected)
        for address, expected in enumerate((1, 3, 5, 7, 1)):
            self.assertEqual(romf._get_read_data(address), expected)

    def test_build_new_roms(self):
        width = 6
        rom = pyrtl.RomBlock(6, 6, [2, 4, 7, 1], build_new_roms=True)
        for i in range(width):
            rom_read_address = pyrtl.Input(width)
            rom_out = pyrtl.Output(width)
            rom_out <<= rom[rom_read_address]
        roms = set()
        for romNet in pyrtl.working_block().logic_subset('m'):
            curr_rom = romNet.op_param[1]
            roms.add(curr_rom)
        self.assertEquals(len(roms), 3)


if __name__ == "__main__":
    unittest.main()
