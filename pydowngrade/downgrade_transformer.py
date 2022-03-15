import xdis
from copy import deepcopy


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
    
    return code
