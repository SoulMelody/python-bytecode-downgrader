import time
import sys

from .downgrade_transformer import downgrade_py39_code_to_py38
from .pyc_io import Py39CompiledFile, output_py38_pyc_file

if __name__ == '__main__':
    pyc = Py39CompiledFile(sys.argv[1])
    with open(sys.argv[2], 'wb') as f:
        py38_code = downgrade_py39_code_to_py38(pyc.code)
        output_py38_pyc_file(py38_code, f, int(time.time()))
