import xdis
from xdis import marsh as xdis_marsh
from xdis.codetype.base import CodeBase
from xdis.magics import magics as xdis_magics

import pathlib
import struct
import time
import typing
import types


# ===== HACK =====
# Okay this horrible hack is a monkey patch for xdis's version independent
# marshaller until I can upstream a fix. Currently it keeps around a
# a dictionary of (type: dump_function). It adds in a mapping for
# `Code3: dump_code3`. However, since we mostly deal with Code38 objects here,
# this lookup fails. In this case they have a:
#
#     if isinstance(x, Code2):
#         self.dispatch[Code2](self, x)
#         return
#     elif isinstance(x, Code3):
#         self.dispatch[Code3](self, x)
#         return
#
# except Code3 inherits from Code2, so the Code2 dispatcher always gets
# triggered.
xdis_marsh._Marshaller.dispatch[xdis.Code38] = xdis_marsh._Marshaller.dump_code3
# ================


def transform_code_to_portable(
    code: typing.Union[CodeBase, types.CodeType]
) -> xdis.Code38:
    """
    xdis has a feature whereby code objects from the same interpreter as the one
    running will be loaded as native Python code objects instead of xdis's own
    cross-version `xdis.Code` object.

    This function allows converting to the flexible `xdis.Code` object, if the
    passed in code is already an xdis code instance, it just returns it
    directly.
    """
    code = xdis.codeType2Portable(code)
    code.co_consts = list(code.co_consts)
    for i, const in enumerate(code.co_consts):
        try:
            code.co_consts[i] = xdis.codeType2Portable(const, (3, 8, 3))
        except TypeError:
            pass
    return code


class Py39CompiledFile:
    code: xdis.Code38

    def __init__(self, filename: pathlib.Path) -> None:
        loaded_module = xdis.load_module(str(filename))

        version = loaded_module[0]
        if version[:2] != (3, 9):
            raise ValueError("Only Python 3.9 files are supported")

        self.code = transform_code_to_portable(loaded_module[3])


def output_py38_pyc_file(
    code: xdis.Code38, file: typing.BinaryIO, timestamp: typing.Optional[int] = None
):
    """
    Takes the `code` argument representing the module code and writes it in a
    pyc file format in `file`.
    """
    if timestamp is None:
        timestamp = int(time.time())

    magic_bytes = xdis_magics["3.8.3"]
    file.write(magic_bytes)

    # 0 means a timestamp based validated pyc (instead of hash based)
    file.write(struct.pack("<I", 0))
    file.write(struct.pack("<I", timestamp))

    # Size of the source file, we just put 0 here.
    file.write(struct.pack("<I", 0))

    code = code.freeze()
    serialized_code = xdis_marsh.dumps(code, python_version=(3, 8, 3))
    file.write(serialized_code)
