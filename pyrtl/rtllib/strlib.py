__author__ = 'johnw'


def str_to_int_array(string, base=16):
    """
    Converts a string to an array of integer values according to the
    base specified

    :return: [int]

    int numbers must be whitespace delimited

    Example:
    "13 a3 3c" => [0x13, 0xa3, 0x3c]
    """

    hex_strings = string.split()
    return [int(hex_str, base) for hex_str in hex_strings]
