import pytest
from pydowngrade import py39_reader
from pathlib import Path


TEST_FOLDER = Path(__file__).resolve().parent
TEST_FILES_FOLDER = TEST_FOLDER / 'test_files'


def test_fails_on_non_python_3_9_code():
    py38_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-38.pyc'
    with pytest.raises(ValueError) as excinfo:
        py39_reader.Py39CompiledFile(py38_hello_world)

    assert "Only Python 3.9 files are supported" in str(excinfo.value)


def test_loads_python_3_9_code():
    py39_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-39.pyc'
    compiled_file = py39_reader.Py39CompiledFile(py39_hello_world)

    assert compiled_file.code is not None


def test_loaded_code_properties():
    py39_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-39.pyc'
    compiled_file = py39_reader.Py39CompiledFile(py39_hello_world)

    module_code = compiled_file.code
    assert 'test' in module_code.co_names

    function_code = module_code.co_consts[0]
    assert function_code.co_argcount == 0
    assert function_code.co_name == 'test'
    assert function_code.co_consts == (None, 'Hello World')


def test_loaded_code_bytecode():
    py39_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-39.pyc'
    compiled_file = py39_reader.Py39CompiledFile(py39_hello_world)

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
