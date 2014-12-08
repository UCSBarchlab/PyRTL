"""
This requires pydevtools (https://code.google.com/p/pydevtools/).
They can be installed with: easy_install BinTools
This simply contains some helper functions for the MIPS pipeline to build memory based on an ELF file.
C programs which output .data and .bss ELF sections may not be fully supported.
"""

from itertools import islice
from bintools.elf import ELF

def chunk(it, size):
    it = iter(it)
    return iter(lambda: ''.join(tuple(islice(it, size))), '')

def load_elf(file):
    return ELF(file)

def get_entry(elf):
    return elf.header.entry

def build_program_memory(elf):
    memory = {}

    for header in elf.sect_headers:
        h = header

        if not h.is_loadable():
            continue

        address = h.addr
        data_words = [int(i.encode('hex'), 16) for i in list(chunk(h.data, 1))]
        for word in data_words:
            memory[address] = word
            address += 1

    return memory
