from pathlib import Path
import subprocess
import pytest
import xdis
from pydowngrade import pyc_io


# Convenient pathlib Path to the `test_files` folder.
TEST_FOLDER = Path(__file__).resolve().parent
TEST_FILES_FOLDER = TEST_FOLDER / 'test_files'


# Decorator to mark tests that need a python 3.8 executable.
try:
    subprocess.check_output(['python3.8', '--version'])
    PY_38_COMMAND = ['python3.8']
except OSError:
    PY_38_COMMAND = None

if PY_38_COMMAND is None:
    try:
        subprocess.check_output(['py', '-3.8', '--version'])
        PY_38_COMMAND = ['py', '-3.8']
    except OSError:
        PY_38_COMMAND = None


can_execute_python_3_8 = pytest.mark.skipif(
    PY_38_COMMAND is None,
    reason="A `python3.8` or `py -3.8` executable is required in PATH"
)


def load_python_pyc_file(file):
    """Testing utility function to read a Python file into a version
    independent xdis.Code* object"""
    loaded_code_module = xdis.load_module(str(file))[3]
    return pyc_io.transform_code_to_portable(loaded_code_module)
