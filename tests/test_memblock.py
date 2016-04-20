import unittest
import pyrtl


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
                                     name='self.memory')

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_memblock_simple(self):
        self.output1 <<= self.memory[self.mem_read_address1]
        self.output2 <<= self.memory[self.mem_read_address2]
        self.memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check()

    def test_memblock_assign_with_extention(self):
        big_output = pyrtl.Output(self.bitwidth+1, "big_output")
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
                                     name='self.memory', romdata=self.data)

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_read(self):
        self.output1 <<= self.memory[self.in1]

    def test_direct_assignment_error(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.memory[self.in1] = self.in2

    def test_write(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.memory[self.in1] <<= 5

    # test does not check functionality, just that it will generate hardware
    def test_rom_to_rom_direct_operation(self):
        temp = (self.memory[self.in1] == self.memory[self.in2])
        temp = (self.memory[self.in1] != self.memory[self.in2])
        temp = (self.memory[self.in1] & self.memory[self.in2])
        temp = (self.memory[self.in1] | self.memory[self.in2])
        temp = (self.memory[self.in1] + self.memory[self.in2])
        temp = (self.memory[self.in1] - self.memory[self.in2])
        temp = (self.memory[self.in1] * self.memory[self.in2])
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
            return 2 * (8-address) + 1

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

    def test_valid_get_read(self):
        rom, romf = self.sample_roms()
        for address, expected in enumerate((2, 4, 7, 1)):
            self.assertEqual(rom._get_read_data(address), expected)
        for address, expected in enumerate((1, 3, 5, 7, 1)):
            self.assertEqual(romf._get_read_data(address), expected)


if __name__ == "__main__":
    unittest.main()
