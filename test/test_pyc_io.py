import pytest
import xdis
from pydowngrade import pyc_io

from utils import TEST_FILES_FOLDER, load_python_pyc_file


def test_fails_on_non_python_3_9_code():
    py38_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-38.pyc'
    with pytest.raises(ValueError) as excinfo:
        pyc_io.Py39CompiledFile(py38_hello_world)

    assert "Only Python 3.9 files are supported" in str(excinfo.value)


def test_loads_python_3_9_code():
    py39_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-39.pyc'
    compiled_file = pyc_io.Py39CompiledFile(py39_hello_world)

    assert compiled_file.code is not None


def test_loaded_code_properties():
    py39_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-39.pyc'
    compiled_file = pyc_io.Py39CompiledFile(py39_hello_world)

    module_code = compiled_file.code
    assert 'test' in module_code.co_names

    function_code = module_code.co_consts[0]
    assert function_code.co_argcount == 0
    assert function_code.co_name == 'test'
    assert function_code.co_consts == (None, 'Hello World')


def test_loaded_code_bytecode():
    py39_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-39.pyc'
    compiled_file = pyc_io.Py39CompiledFile(py39_hello_world)

    module_code = compiled_file.code
    assert module_code.co_code == bytes([
        # LOAD_CONST     0 (code object for test function)
        100, 0,
        # LOAD_CONST     1 ('test')
        100, 1,
        # MAKE_FUNCTION  0
        132, 0,
        # STORE_NAME     0 (test)
        90, 0,
        # LOAD_CONST     2 (None)
        100, 2,
        # RETURN_VALUE
        83, 0,
    ])

    function_code = module_code.co_consts[0]
    assert function_code.co_code == bytes([
        # LOAD_GLOBAL    0 (print)
        116, 0,
        # LOAD_CONST     1 ('Hello World')
        100, 1,
        # CALL_FUNCTION  1
        131, 1,
        # POP_TOP
        1, 0,
        # LOAD_CONST     0 (None)
        100, 0,
        # RETURN_VALUE
        83, 0,
    ])


def assert_code_objects_equal_except_constants(actual_code, expected_code):
    """Compares two code objects to see if everything except co_consts is
    the same"""
    assert actual_code.co_argcount == expected_code.co_argcount
    assert actual_code.co_posonlyargcount == expected_code.co_posonlyargcount
    assert actual_code.co_kwonlyargcount == expected_code.co_kwonlyargcount
    assert actual_code.co_nlocals == expected_code.co_nlocals
    assert actual_code.co_stacksize == expected_code.co_stacksize
    assert actual_code.co_flags == expected_code.co_flags
    assert actual_code.co_code == expected_code.co_code
    assert actual_code.co_names == expected_code.co_names
    assert actual_code.co_varnames == expected_code.co_varnames
    assert actual_code.co_filename == expected_code.co_filename
    assert actual_code.co_name == expected_code.co_name
    assert actual_code.co_firstlineno == expected_code.co_firstlineno
    assert actual_code.co_lnotab == expected_code.co_lnotab
    assert actual_code.co_freevars == expected_code.co_freevars
    assert actual_code.co_cellvars == expected_code.co_cellvars


def test_py_38_file_roundtrips(tmp_path):
    # Load a known 3.8 file.
    py38_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-38.pyc'

    # Load up the code through xdis.
    expected_code = load_python_pyc_file(py38_hello_world).freeze()

    # Open an output pyc file and write our module to it
    output_pyc_file = tmp_path / 'output.pyc'
    with output_pyc_file.open('wb') as f:
        pyc_io.output_py38_pyc_file(expected_code, f)

    # Load the written file and compare.
    actual_code = load_python_pyc_file(output_pyc_file).freeze()
    assert_code_objects_equal_except_constants(expected_code, actual_code)
    # Compare all the constants *except* the nested code object which doesn't
    # have an equality operator.
    assert actual_code.co_consts[1:] == expected_code.co_consts[1:]

    actual_nested_code = actual_code.co_consts[0]
    expected_nested_code = expected_code.co_consts[0]
    assert_code_objects_equal_except_constants(actual_nested_code, expected_nested_code)

