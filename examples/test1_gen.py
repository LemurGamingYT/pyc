from ctypes import CDLL

lib = CDLL('C:/Programming/Python/pyc/examples/test1.dll')
def double(x: int) -> int:
    return lib.double(x)

