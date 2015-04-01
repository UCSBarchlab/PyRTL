NAND_TEMPLATE = """{M1} {output} {InputB} Vdd Vdd PMOS
{M2} {output} {InputA} Vdd Vdd PMOS
{M4} {node} {InputB} 0 0 NMOS
{M3} {output} {InputA} {node} 0 NMOS"""
