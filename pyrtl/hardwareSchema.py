
def hardware_schema():
    ''' This function holds the schemas to check that any json hardware
        representation conforms to the same requirements

        All components except for inputs should have some driver
        If the driving logic comes from a memory operation it is listed
        under the memory's read operations
        If the driving logic does not list an operation it is a simple
        assignment operation (destination = argument)

        Arguments should always be listed from left to right as one might
        read them in a language like verilog
        EX. a + b becomes op='+', args=[a,b]
        Ex. a ? b : c becomes op='?', args=[a, b, c]
        Ex. {a, b} becomes op='concat', args=[a,b]

        If the module does not have a primary component (inputs, outputs,
        registers, wires, memory) their field should be included with an
        empty list

    '''

    nameSchema = {
        "description": "The component's name",
        "type": "string"
    }

    bitwidthSchema = {
        "description": "The number of bits this component contains",
        "type": "integer"
    }

    inputSchema = {
        "name": nameSchema,
        "bitwidth": bitwidthSchema
    }

    wireSchema = {
        "name": nameSchema,
        "bitwidth": bitwidthSchema,
        "Constant value": {
            "description": "If this is a constant this field holds its constant value",
            "type": "integer"
        },
        "driver": {
            "description": "The operation or wire that drives this component",
            "type": "object",
            "properties": {
                "op": {
                    "description": "Logical operation whose output is driving this component",
                    "type": "string"
                },
                "args": {
                    "description": """A list of the arguments of the operation,
                                      in order of left to right""",
                    "type": "array",
                    "items": {
                        "description": "Individual arguments",
                        "type": "string"
                    }
                },
            },
            "required": ["op", "args"]
        }
    }

    regSchema = {
        "name": nameSchema,
        "bitwidth": bitwidthSchema,
        "Constant value": {
            "description": "If this is a constant this field holds its constant value",
            "type": "integer"
        },
        "src": {
            "description": "The component input into a register",
            "type": "string"
        },
        "rst val": {
            "description": "If this is a register, this lists what it should be reset to",
            "type": "integer"
        },
    }

    memorySchema = {
        "name": nameSchema,
        "bitwidth": bitwidthSchema,
        "size": {
            "description": "The number of addressable locations",
            "type": "integer"
        },
        "initial values": {
            "description": "For ROM memory this outlines each address' initial value as an integer",
            "type": "array",
            "items": {
                "description": """The index in the list is the memory address each
                                  intial value maps to""",
                "type": "object",
                "properties": {
                    "start addr": {
                        "description": "Beginning address for the list of initial values",
                        "type": "integer"
                    },
                    "values": {
                        "description": """"list of the initial values, each index is
                                           an offset from the start addr""",
                        "type": "array",
                        "items": {
                            "description": """Inital value for memory address
                                              [start addr + list index]""",
                            "type": "integer"
                        }
                    }
                },
                "required": ["start addr", "values"]
            }
        },
        "reads": {
            "description": "A list of all read operations ocurring on this memory",
            "type": "array",
            "items": {
                "description": "A single memory read operation",
                "type": "object",
                "properties": {
                    "destination": {
                        "description": "The component receiving the result of the read operation",
                        "type": "string"
                    },
                    "addr": {
                        "description": "The wire name that selects the memory address to be read",
                        "type": "string"
                    }
                },
                "required": ["destination", "addr"]
            }
        },
        "writes": {
            "description": "A list of all the write operations to this memory",
            "type": "array",
            "items": {
                "description": "A single memory write operation",
                "type": "object",
                "properties": {
                    "addr": {
                        "description": """The component that selects the
                                          memory address to be written""",
                        "type": "string"
                    },
                    "data src": {
                        "description": """The component that provides the
                                          data to be written to memory""",
                        "type": "string"
                    },
                    "w.e": {
                        "description": "The component that controls the write enable if applicable",
                        "type": "string"
                    },
                },
                "required": ["addr", "data src"]
            }
        }
    }

    exportSchema = {
        # necessary for version control
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "JSON Hardware representation",
        "type": "object",
        "properties": {
            "module": {
                "description": "The top level module",
                "type": "object",
                "properties": {
                    "name": {
                        "description": "The module name",
                        "type": "string"
                    },
                    "inputs": {
                        "description": "List of inputs to the module",
                        "type:": "array",
                        "items": {
                            "description": "An input into the module",
                            "type": "object",
                            "properties": inputSchema,
                            "required": ["name", "bitwidth"]
                        },
                        "uniqueItems": True
                    },
                    "outputs": {
                        "description": "List of the module's outputs",
                        "type": "array",
                        "items": {
                            "description": "An output of the module",
                            "type": "object",
                            "properties": wireSchema,
                            "required": ["name", "bitwidth", "driver"]
                        },
                        "uniqueItems": True
                    },
                    "wires": {
                        "description": "List of the internal wires in the module",
                        "type": "array",
                        "items": {
                            "description": "A wire in the module",
                            "type": "object",
                            "properties": wireSchema,
                            "required": ["name", "bitwidth"]
                        },
                        "uniqueItems": True
                    },
                    "registers": {
                        "description": "List of the internal registers in the module",
                        "type": "array",
                        "items": {
                            "description": "A register in the module",
                            "type": "object",
                            "properties": regSchema,
                            "required": ["name", "bitwidth", "src"]
                        },
                        "uniqueItems": True
                    },
                    "memories": {
                        "description": "List of memories and their respective accesses",
                        "type": "array",
                        "items": {
                            "description": "A single memory module",
                            "type": "object",
                            "properties": memorySchema,
                            "required": ['name', 'bitwidth', 'size']
                        },
                        "uniqueItems": True
                    },
                },
                "required": ["name", "inputs", "outputs",
                             "wires", "registers", "memories"]
            }
        }
    }

    return exportSchema
