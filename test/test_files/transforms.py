def assertion():
    assert 1 == 2

def is_op():
    return 1 is 1

def not_is_op():
    return 1 is not 1

def in_op():
    return 0 in ()

def not_in_op():
    return 0 not in ()

def comparison_op():
    return 0 == 0

def exception_match_op():
    try:
        int('hi')
        return 0
    except ValueError:
        return 1
