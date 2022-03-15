import xdis
import typing
from copy import deepcopy


# Python 3.9 specific opcodes
LOAD_ASSERTION_ERROR_OPCODE = 74
IS_OP_OPCODE = 117
CONTAINS_OP_OPCODE = 118
JUMP_IF_NOT_EXC_MATCH_OPCODE = 121
#
LOAD_GLOBAL_OPCODE = 116
COMPARE_OP_OPCODE = 107

COMPARE_OP_IS_OPERATOR = 8
COMPARE_OP_IN_OPERATOR = 6


def downgrade_py39_code_to_py38(code: xdis.Code38) -> xdis.Code38:
    """
    Transforms an xdis loaded Python 3.9 code object to a Python 3.8 code
    object. This transforms any 3.9 specific opcodes into their 3.8 equivalents.

    Note that xdis represents both 3.9 and 3.8 code objects with the same type.
    """
    # Make a copy of the code object, we don't want to mutate it in-place.
    code = deepcopy(code)

    code.co_consts = list(code.co_consts)
    # Transform any nested stored code objects first.
    for i, const in enumerate(code.co_consts):
        if not isinstance(const, xdis.Code38):
            continue
        code.co_consts[i] = downgrade_py39_code_to_py38(const)

    new_code = []
    for i in range(0, len(code.co_code), 2):
        opcode, oparg = code.co_code[i], code.co_code[i + 1]

        if opcode not in (LOAD_ASSERTION_ERROR_OPCODE, IS_OP_OPCODE, CONTAINS_OP_OPCODE, JUMP_IF_NOT_EXC_MATCH_OPCODE):
            new_code.append(opcode)
            new_code.append(oparg)
            continue

        # Transform LOAD_ASSERTION_ERROR back to
        # LOAD_GLOBAL   n ('AssertionError')
        if opcode == LOAD_ASSERTION_ERROR_OPCODE:
            assertion_error_name_idx = get_or_add_name('AssertionError', code)
            assert assertion_error_name_idx <= 255
            new_code.append(LOAD_GLOBAL_OPCODE)
            new_code.append(assertion_error_name_idx)
        # Transform IS_OP, CONTAINS_OP and JUMP_IF_NOT_EXC_MATCH back to
        # COMPARE_OP.
        if opcode == IS_OP_OPCODE:
            # Convert to `COMPARE_OP  8 (is)` or `COMPARE_OP  9 (is not)`
            new_code.append(COMPARE_OP_OPCODE)
            new_code.append(COMPARE_OP_IS_OPERATOR + bool(oparg))
        if opcode == CONTAINS_OP_OPCODE:
            # Convert to `COMPARE_OP  6 (in)` or `COMPARE_OP  7 (not in)`
            new_code.append(COMPARE_OP_OPCODE)
            new_code.append(COMPARE_OP_IN_OPERATOR + bool(oparg))

    code.co_code = bytes(new_code)    
    return code.freeze()


def get_or_add_name(name: str, code: xdis.Code38) -> int:
    """Retrieves the index of `name` in the `names` list. Or if it doesn't
    exist, appends it to the end of the names and returns that index.
    """
    try:
        return code.co_names.index(name)
    except ValueError:
        existing_names = list(code.co_names)
        existing_names.append(name)
        code.co_names = tuple(existing_names)
        return len(code.co_names) - 1
