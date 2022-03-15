from xdis.std import make_std_api
from pydowngrade import pyc_io
from pydowngrade.downgrade_transformer import downgrade_py39_code_to_py38
from utils import TEST_FILES_FOLDER, load_python_pyc_file


dis_module_3_8 = make_std_api(python_version=(3, 8, 1))
dis_module_3_9 = make_std_api(python_version=(3, 9, 1))


def test_transformer_produces_new_code_object():
    py_39_hello_world = TEST_FILES_FOLDER / 'hello_world.cpython-39.pyc'
    code = pyc_io.Py39CompiledFile(py_39_hello_world).code

    transformed = downgrade_py39_code_to_py38(code)
    # We don't expect any changes in the module code as it doesn't use any
    # 3.9 specific opcodes.
    assert transformed.co_code == code.co_code


def test_transform_load_assertion_opcode():
    # Check that the
    #     def assertion():
    #         assert 1 == 2
    # function goes from
    #     LOAD_ASSERTION_ERROR
    # to
    #     LOAD_GLOBAL  0 (AssertionError)
    py_39_file = TEST_FILES_FOLDER / 'transforms.cpython-39.pyc'
    py_39_code = pyc_io.Py39CompiledFile(py_39_file).code

    assertion_function = py_39_code.co_consts[0]
    assert assertion_function.co_name == 'assertion'
    assert assertion_function.co_consts == (None, 1, 2)
    assert assertion_function.co_names == ()
    assert 'LOAD_ASSERTION_ERROR' in dis_module_3_9.Bytecode(assertion_function).dis()

    py_38_code = downgrade_py39_code_to_py38(py_39_code)
    assertion_function = py_38_code.co_consts[0]
    assert assertion_function.co_name == 'assertion'
    assert assertion_function.co_consts == (None, 1, 2)
    assert assertion_function.co_names == ('AssertionError', )
    assert 'LOAD_GLOBAL' in dis_module_3_8.Bytecode(assertion_function).dis()

def test_transform_load_assertion_against_known_good():
    # Same test as above but against a Python 3.8 compiled version of the file.
    py_39_file = TEST_FILES_FOLDER / 'transforms.cpython-39.pyc'
    py_39_code = pyc_io.Py39CompiledFile(py_39_file).code

    py_38_file = TEST_FILES_FOLDER / 'transforms.cpython-38.pyc'
    py_38_code = load_python_pyc_file(py_38_file)

    expected_assertion_function = py_38_code.co_consts[0]
    assert expected_assertion_function.co_name == 'assertion'

    py_39_assertion_function = py_39_code.co_consts[0]
    assert py_39_assertion_function.co_name == 'assertion'
    actual_assertion_function = downgrade_py39_code_to_py38(py_39_assertion_function)

    assert actual_assertion_function.co_code == expected_assertion_function.co_code
