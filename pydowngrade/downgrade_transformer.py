import xdis
import bisect
from copy import deepcopy

# Python 3.9 specific opcodes
LOAD_ASSERTION_ERROR_OPCODE = 74
IS_OP_OPCODE = 117
CONTAINS_OP_OPCODE = 118
RERAISE_OPCODE = 48
LIST_EXTEND_OPCODE = 162
SET_UPDATE_OPCODE = 163  # TODO
JUMP_IF_NOT_EXC_MATCH_OPCODE = 121  # TODO

LOAD_GLOBAL_OPCODE = 116
COMPARE_OP_OPCODE = 107
COMPARE_OP_IS_OPERATOR = 8
COMPARE_OP_IN_OPERATOR = 6
END_FINALLY_OPCODE = 88
BUILD_LIST_OPCODE = 103

NOP_OPCODE = 9
RETURN_VALUE_OPCODE = 83
POP_EXCEPT_OPCODE = 89
LOAD_CONST_OPCODE = 100
LOAD_NAME_OPCODE = 101
JUMP_FORWARD_OPCODE = 110
JUMP_ABSOLUTE_OPCODE = 113
POP_JUMP_IF_FALSE_OPCODE = 114
POP_JUMP_IF_TRUE_OPCODE = 115
CALL_FUNCTION_OPCODE = 131


def downgrade_py39_code_to_py38(code: xdis.Code38) -> xdis.Code38:
    """
    Transforms an xdis loaded Python 3.9 code object to a Python 3.8 code
    object. This transforms any 3.9 specific opcodes into their 3.8 equivalents.

    Note that xdis represents both 3.9 and 3.8 code objects with the same type.
    """
    # Make a copy of the code object, we don't want to mutate it in-place.
    code = deepcopy(code)
    inc_offset = 0
    abstract_offsets = [(0, inc_offset)]

    code.co_consts = list(code.co_consts)
    # Transform any nested stored code objects first.
    for i, const in enumerate(code.co_consts):
        if not isinstance(const, xdis.Code38):
            continue
        code.co_consts[i] = downgrade_py39_code_to_py38(const)

    new_code = []
    for i in range(0, len(code.co_code), 2):
        opcode, oparg = code.co_code[i], code.co_code[i + 1]

        if opcode not in (
            LOAD_ASSERTION_ERROR_OPCODE,
            IS_OP_OPCODE,
            CONTAINS_OP_OPCODE,
            RERAISE_OPCODE,
            LIST_EXTEND_OPCODE,
        ):
            new_code.append(opcode)
            new_code.append(oparg)
            continue

        # Transform LOAD_ASSERTION_ERROR back to
        # LOAD_GLOBAL   n ('AssertionError')
        if opcode == LOAD_ASSERTION_ERROR_OPCODE:
            assertion_error_name_idx = get_or_add_name("AssertionError", code)
            assert assertion_error_name_idx <= 255
            new_code.append(LOAD_GLOBAL_OPCODE)
            new_code.append(assertion_error_name_idx)
        elif opcode == LIST_EXTEND_OPCODE:
            list_obj = list(code.co_consts[new_code[-1]])
            eval_idx = get_or_add_name("eval", code)
            new_code[-4] = LOAD_NAME_OPCODE
            new_code[-3] = eval_idx
            list_repr_idx = get_or_add_const(str(list_obj), code)
            new_code[-2] = LOAD_CONST_OPCODE
            new_code[-1] = list_repr_idx
            new_code.append(CALL_FUNCTION_OPCODE)
            new_code.append(1)
        # Transform IS_OP, CONTAINS_OP and JUMP_IF_NOT_EXC_MATCH back to
        # COMPARE_OP.
        elif opcode == IS_OP_OPCODE:
            # Convert to `COMPARE_OP  8 (is)` or `COMPARE_OP  9 (is not)`
            new_code.append(COMPARE_OP_OPCODE)
            new_code.append(COMPARE_OP_IS_OPERATOR + bool(oparg))
        elif opcode == CONTAINS_OP_OPCODE:
            # Convert to `COMPARE_OP  6 (in)` or `COMPARE_OP  7 (not in)`
            new_code.append(COMPARE_OP_OPCODE)
            new_code.append(COMPARE_OP_IN_OPERATOR + bool(oparg))
        elif opcode == RERAISE_OPCODE:
            if new_code[-6] == POP_EXCEPT_OPCODE and oparg == 0:
                inc_offset += 2
                abstract_offsets.append((i + inc_offset, inc_offset))
                new_code = (
                    new_code[:-4]
                    + [JUMP_FORWARD_OPCODE, 2, END_FINALLY_OPCODE, oparg]
                    + new_code[-4:]
                )
            elif new_code[-8] == POP_EXCEPT_OPCODE and oparg == 0:
                inc_offset += 2
                abstract_offsets.append((i + inc_offset, inc_offset))
                new_code = (
                    new_code[:-6]
                    + [JUMP_FORWARD_OPCODE, 2, END_FINALLY_OPCODE, oparg]
                    + new_code[-6:]
                )
            elif (
                new_code[-4] == POP_EXCEPT_OPCODE
                and new_code[-2] == JUMP_FORWARD_OPCODE
                and new_code[-1] == 2
                and oparg == 0
            ):
                new_code = new_code[:-2] + [
                    JUMP_FORWARD_OPCODE,
                    2,
                    END_FINALLY_OPCODE,
                    oparg,
                ]
            else:
                new_code.append(END_FINALLY_OPCODE)
                new_code.append(oparg)

    final_code = []
    for i in range(0, len(new_code), 2):
        opcode, oparg = new_code[i], new_code[i + 1]

        if opcode in (
            POP_JUMP_IF_TRUE_OPCODE,
            POP_JUMP_IF_FALSE_OPCODE,
            JUMP_ABSOLUTE_OPCODE,
        ):
            final_code.append(opcode)
            add_offset = max(
                0,
                bisect.bisect_right(abstract_offsets, (oparg, oparg)) - 1,
            )
            final_code.append(oparg + abstract_offsets[add_offset][1])
        elif opcode in (JUMP_FORWARD_OPCODE,):
            final_code.append(opcode)
            src_offset = max(
                0,
                bisect.bisect_right(abstract_offsets, (i, oparg)) - 1,
            )
            target = i + oparg + 2
            dst_offset = max(
                0,
                bisect.bisect_right(abstract_offsets, (target, oparg)) - 1,
            )
            if src_offset != dst_offset:
                final_code.append(
                    oparg
                    + abstract_offsets[dst_offset][1]
                    - abstract_offsets[src_offset][1]
                )
            else:
                final_code.append(oparg)
        else:
            final_code.append(opcode)
            final_code.append(oparg)

    code.co_code = bytes(final_code)
    return code.freeze()


def get_or_add_const(const: str, code: xdis.Code38) -> int:
    """Retrieves the index of `name` in the `names` list. Or if it doesn't
    exist, appends it to the end of the names and returns that index.
    """
    try:
        return code.co_consts.index(const)
    except ValueError:
        existing_consts = list(code.co_consts)
        existing_consts.append(const)
        code.co_consts = tuple(existing_consts)
        return len(code.co_consts) - 1


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
