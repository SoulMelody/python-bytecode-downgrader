# These sets of tests rely on being able to execute Python 3.8 code.
import subprocess
from pydowngrade import pyc_io
from utils import (
    TEST_FILES_FOLDER, PY_38_COMMAND, can_execute_python_3_8, load_python_pyc_file
)


@can_execute_python_3_8
def test_can_import_known_good_python_3_8_pyc_file(tmp_path):
    # Basic sanity check to make sure a known good python 3.8 pyc file works.
    py38_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-38.pyc'
    temporary_hello_world = tmp_path / 'hello_world.pyc'

    # Copy just the pyc file to a temporary directory
    temporary_hello_world.write_bytes(py38_hello_world.read_bytes())

    output = subprocess.check_output(
        PY_38_COMMAND + ['-c', 'import hello_world; hello_world.test()'],
        cwd=str(tmp_path), encoding='utf-8'
    )
    assert output == 'Hello World\n'


@can_execute_python_3_8
def test_can_import_roundtripped_python_3_8_pyc_file(tmp_path):
    # Now the fun part, try reading the known good 3.8 pyc file. Saving it out
    # to a pyc by ourselves and seeing if that will import.
    py38_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-38.pyc'
    loaded_hello_world = load_python_pyc_file(py38_hello_world).freeze()

    temporary_hello_world = tmp_path / 'hello_world.pyc'
    with temporary_hello_world.open('wb') as f:
        pyc_io.output_py38_pyc_file(loaded_hello_world, f)

    # Try running the hello world.
    output = subprocess.check_output(
        PY_38_COMMAND + ['-c', 'import hello_world; hello_world.test()'],
        cwd=str(tmp_path), encoding='utf-8'
    )
    assert output == 'Hello World\n'
