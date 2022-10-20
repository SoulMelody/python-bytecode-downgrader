import bisect
from copy import deepcopy

import xdis

# Python 3.9 specific opcodes
SET_UPDATE_OPCODE = 163  # TODO
JUMP_IF_NOT_EXC_MATCH_OPCODE = 121  # TODO

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
    inc_offset = 0
    absolute_offsets = [(0, inc_offset)]

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
            xdis.opcode_39.LOAD_ASSERTION_ERROR,
            xdis.opcode_39.IS_OP,
            xdis.opcode_39.CONTAINS_OP,
            xdis.opcode_39.RERAISE,
            xdis.opcode_39.LIST_EXTEND,
        ):
            new_code.append(opcode)
            new_code.append(oparg)
            continue

        # Transform LOAD_ASSERTION_ERROR back to
        # LOAD_GLOBAL   n ('AssertionError')
        if opcode == xdis.opcode_39.LOAD_ASSERTION_ERROR:
            assertion_error_name_idx = get_or_add_name("AssertionError", code)
            assert assertion_error_name_idx <= 255
            new_code.append(xdis.opcode_38.LOAD_GLOBAL)
            new_code.append(assertion_error_name_idx)
        elif opcode == xdis.opcode_39.LIST_EXTEND:
            list_obj = list(code.co_consts[new_code[-1]])
            eval_idx = get_or_add_name("eval", code)
            new_code[-4] = xdis.opcode_38.LOAD_NAME
            new_code[-3] = eval_idx
            list_repr_idx = get_or_add_const(str(list_obj), code)
            new_code[-2] = xdis.opcode_38.LOAD_CONST
            new_code[-1] = list_repr_idx
            new_code.append(xdis.opcode_38.CALL_FUNCTION)
            new_code.append(1)
        # Transform IS_OP, CONTAINS_OP back to COMPARE_OP.
        elif opcode == xdis.opcode_39.IS_OP:
            # Convert to `COMPARE_OP  8 (is)` or `COMPARE_OP  9 (is not)`
            new_code.append(xdis.opcode_38.COMPARE_OP)
            new_code.append(COMPARE_OP_IS_OPERATOR + bool(oparg))
        elif opcode == xdis.opcode_39.CONTAINS_OP:
            # Convert to `COMPARE_OP  6 (in)` or `COMPARE_OP  7 (not in)`
            new_code.append(xdis.opcode_38.COMPARE_OP)
            new_code.append(COMPARE_OP_IN_OPERATOR + bool(oparg))
        elif opcode == xdis.opcode_39.RERAISE:
            if (
                len(new_code) >= 6
                and new_code[-6] == xdis.opcode_38.POP_EXCEPT
                and oparg == 0
            ):
                inc_offset += 2
                absolute_offsets.append((i + inc_offset, inc_offset))
                new_code = (
                    new_code[:-4]
                    + [
                        xdis.opcode_38.JUMP_FORWARD,
                        2,
                        xdis.opcode_38.END_FINALLY,
                        oparg,
                    ]
                    + new_code[-4:]
                )
            elif (
                len(new_code) >= 8
                and new_code[-8] == xdis.opcode_38.POP_EXCEPT
                and oparg == 0
            ):
                inc_offset += 2
                absolute_offsets.append((i + inc_offset, inc_offset))
                new_code = (
                    new_code[:-6]
                    + [
                        xdis.opcode_38.JUMP_FORWARD,
                        2,
                        xdis.opcode_38.END_FINALLY,
                        oparg,
                    ]
                    + new_code[-6:]
                )
            elif len(new_code) >= 4 and (
                new_code[-4] == xdis.opcode_38.POP_EXCEPT
                and new_code[-2] == xdis.opcode_38.JUMP_FORWARD
                and new_code[-1] == 2
                and oparg == 0
            ):
                new_code = new_code[:-2] + [
                    xdis.opcode_38.JUMP_FORWARD,
                    2,
                    xdis.opcode_38.END_FINALLY,
                    oparg,
                ]
            elif (
                len(new_code) >= 4
                and new_code[-4] == xdis.opcode_38.POP_EXCEPT
                and oparg == 0
            ):
                inc_offset += 2
                absolute_offsets.append((i + inc_offset, inc_offset))
                new_code = (
                    new_code[:-2]
                    + [
                        xdis.opcode_38.JUMP_FORWARD,
                        2,
                        xdis.opcode_38.END_FINALLY,
                        oparg,
                    ]
                    + new_code[-2:]
                )
            else:
                new_code.append(xdis.opcode_38.END_FINALLY)
                new_code.append(oparg)

    final_code = []
    target_base = 0
    for i in range(0, len(new_code), 2):
        opcode, oparg = new_code[i], new_code[i + 1]

        if opcode in xdis.opcode_38.JABS_OPS:
            final_code.append(opcode)
            target = target_base + oparg
            add_offset = max(
                0,
                bisect.bisect_right(absolute_offsets, (target, target)) - 1,
            )
            final_code.append(oparg + absolute_offsets[add_offset][1])
        elif opcode in xdis.opcode_38.JREL_OPS:
            target = i + target_base + oparg + 2
            final_code.append(opcode)
            src_offset = max(
                0,
                bisect.bisect_right(absolute_offsets, (i, target)) - 1,
            )
            dst_offset = max(
                0,
                bisect.bisect_right(absolute_offsets, (target, target)) - 1,
            )
            if src_offset != dst_offset:
                final_code.append(
                    oparg
                    + absolute_offsets[dst_offset][1]
                    - absolute_offsets[src_offset][1]
                )
            else:
                final_code.append(oparg)
        else:
            final_code.append(opcode)
            final_code.append(oparg)

        if final_code[-1] >= 256:
            if target_base:
                final_code = final_code[:-3] + [
                    final_code[-1] // 256 - 1,
                    final_code[-2],
                    final_code[-1] % 256,
                ]
            else:
                absolute_offsets = [
                    (offset if offset < len(final_code) else offset + 2, inc_offset)
                    for offset, inc_offset in absolute_offsets
                ]
                final_code = (
                    final_code[:-2]
                    + [xdis.opcode_38.EXTENDED_ARG, final_code[-1] // 256 - 1]
                    + [final_code[-2], final_code[-1] % 256]
                )

        if opcode == xdis.opcode_38.EXTENDED_ARG:
            target_base = 256 * oparg + target_base
        else:
            target_base = 0

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
