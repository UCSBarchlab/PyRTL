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

    int_strings = string.split()
    return [int(int_str, base) for int_str in int_strings]
