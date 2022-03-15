from pathlib import Path
from pydowngrade import downgrade_transformer, pyc_io
from utils import TEST_FILES_FOLDER


PY39_HELLO_WORLD = TEST_FILES_FOLDER / 'hello_world.cpython-39.pyc'


def test_transformer_produces_new_code_object():
    code = pyc_io.Py39CompiledFile(PY39_HELLO_WORLD).code

    transformed = downgrade_transformer.downgrade_py39_code_to_py38(code)
    assert transformed is not None
