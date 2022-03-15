import xdis
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


def get_function_from_module(module: xdis.Code38, function: str) -> xdis.Code38:
    for const in module.co_consts:
        if isinstance(const, xdis.Code38) and const.co_name == function:
            return const
    assert False, "function " + function + " not found in module"


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

    assertion_function = get_function_from_module(py_39_code, 'assertion')
    assert assertion_function.co_name == 'assertion'
    assert assertion_function.co_consts == (None, 1, 2)
    assert assertion_function.co_names == ()
    assert 'LOAD_ASSERTION_ERROR' in dis_module_3_9.Bytecode(assertion_function).dis()

    py_38_code = downgrade_py39_code_to_py38(py_39_code)
    assertion_function = get_function_from_module(py_38_code, 'assertion')
    assert assertion_function.co_name == 'assertion'
    assert assertion_function.co_consts == (None, 1, 2)
    assert assertion_function.co_names == ('AssertionError', )
    assert 'LOAD_ASSERTION_ERROR' not in dis_module_3_8.Bytecode(assertion_function).dis()
    assert 'LOAD_GLOBAL' in dis_module_3_8.Bytecode(assertion_function).dis()

def test_transform_load_assertion_opcode_against_known_good():
    # Same test as above but against a Python 3.8 compiled version of the file.
    py_39_file = TEST_FILES_FOLDER / 'transforms.cpython-39.pyc'
    py_39_code = pyc_io.Py39CompiledFile(py_39_file).code

    py_38_file = TEST_FILES_FOLDER / 'transforms.cpython-38.pyc'
    py_38_code = load_python_pyc_file(py_38_file)

    py_39_assertion_function = get_function_from_module(py_39_code, 'assertion')
    actual_assertion_function = downgrade_py39_code_to_py38(py_39_assertion_function)

    expected_assertion_function = get_function_from_module(py_38_code, 'assertion')

    assert actual_assertion_function.co_code == expected_assertion_function.co_code


def test_transform_is_opcode():
    # Check that
    #     def is_op():
    #         return 1 is 1
    #     def not_is_op():
    #         return 1 is not 1
    # goes from
    #     IS_OP  0
    #     IS_OP  1
    # to
    #     COMPARE_OP  8 (is)
    #     COMPARE_OP  9 (is not)
    py_39_file = TEST_FILES_FOLDER / 'transforms.cpython-39.pyc'
    py_39_code = pyc_io.Py39CompiledFile(py_39_file).code

    is_op_function = get_function_from_module(py_39_code, 'is_op')
    assert 'IS_OP' in dis_module_3_9.Bytecode(is_op_function).dis()
    not_is_op_function = get_function_from_module(py_39_code, 'not_is_op')
    assert 'IS_OP' in dis_module_3_9.Bytecode(not_is_op_function).dis()

    py_38_code = downgrade_py39_code_to_py38(py_39_code)

    is_op_function = get_function_from_module(py_38_code, 'is_op')
    assert 'IS_OP' not in dis_module_3_9.Bytecode(is_op_function).dis()
    assert 'COMPARE_OP           (is)' in dis_module_3_9.Bytecode(is_op_function).dis()
    not_is_op_function = get_function_from_module(py_38_code, 'not_is_op')
    assert 'IS_OP' not in dis_module_3_9.Bytecode(not_is_op_function).dis()
    assert 'COMPARE_OP           (is-not)' in dis_module_3_9.Bytecode(not_is_op_function).dis()


def test_transform_is_opcode_against_known_good():
    # Same test as above but against a Python 3.8 compiled version of the file.
    py_39_file = TEST_FILES_FOLDER / 'transforms.cpython-39.pyc'
    py_39_code = pyc_io.Py39CompiledFile(py_39_file).code

    py_38_file = TEST_FILES_FOLDER / 'transforms.cpython-38.pyc'
    py_38_code = load_python_pyc_file(py_38_file)
    actual_py_38_code = downgrade_py39_code_to_py38(py_39_code)

    expected_is_op_function = get_function_from_module(py_38_code, 'is_op')
    expected_not_is_op_function = get_function_from_module(py_38_code, 'not_is_op')

    assert get_function_from_module(actual_py_38_code, 'is_op').co_code == expected_is_op_function.co_code
    assert get_function_from_module(actual_py_38_code, 'not_is_op').co_code == expected_not_is_op_function.co_code


def test_transform_contains_opcode():
    # Check that
    #     def in_op():
    #         return 0 in ()
    #     def not_in_op():
    #         return 0 not in ()
    # goes from
    #     IN_OP  0
    #     IN_OP  1
    # to
    #     COMPARE_OP  6 (in)
    #     COMPARE_OP  7 (not in)
    py_39_file = TEST_FILES_FOLDER / 'transforms.cpython-39.pyc'
    py_39_code = pyc_io.Py39CompiledFile(py_39_file).code

    in_op_function = get_function_from_module(py_39_code, 'in_op')
    assert 'CONTAINS_OP' in dis_module_3_9.Bytecode(in_op_function).dis()
    not_in_op_function = get_function_from_module(py_39_code, 'not_in_op')
    assert 'CONTAINS_OP' in dis_module_3_9.Bytecode(not_in_op_function).dis()

    py_38_code = downgrade_py39_code_to_py38(py_39_code)

    in_op_function = get_function_from_module(py_38_code, 'in_op')
    assert 'CONTAINS_OP' not in dis_module_3_9.Bytecode(in_op_function).dis()
    assert 'COMPARE_OP           (in)' in dis_module_3_9.Bytecode(in_op_function).dis()
    not_in_op_function = get_function_from_module(py_38_code, 'not_in_op')
    assert 'CONTAINS_OP' not in dis_module_3_9.Bytecode(not_in_op_function).dis()
    assert 'COMPARE_OP           (not-in)' in dis_module_3_9.Bytecode(not_in_op_function).dis()


def test_transform_contains_opcode_against_known_good():
    # Same test as above but against a Python 3.8 compiled version of the file.
    py_39_file = TEST_FILES_FOLDER / 'transforms.cpython-39.pyc'
    py_39_code = pyc_io.Py39CompiledFile(py_39_file).code

    py_38_file = TEST_FILES_FOLDER / 'transforms.cpython-38.pyc'
    py_38_code = load_python_pyc_file(py_38_file)
    actual_py_38_code = downgrade_py39_code_to_py38(py_39_code)

    expected_is_op_function = get_function_from_module(py_38_code, 'in_op')
    expected_not_is_op_function = get_function_from_module(py_38_code, 'not_in_op')

    assert get_function_from_module(actual_py_38_code, 'in_op').co_code == expected_is_op_function.co_code
    assert get_function_from_module(actual_py_38_code, 'not_in_op').co_code == expected_not_is_op_function.co_code
