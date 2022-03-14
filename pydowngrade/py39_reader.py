import xdis
import pathlib


class Py39CompiledFile():
    def __init__(self, filename: pathlib.Path) -> None:
        loaded_module = xdis.load_module(str(filename))

        version = loaded_module[0]
        if version[:2] != (3, 9):
            raise ValueError("Only Python 3.9 files are supported")

        self.code = loaded_module[3]
