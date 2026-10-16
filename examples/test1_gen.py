from ctypes import CDLL

lib = CDLL('C:/Programming/Python/pyc/examples/test1.dll')

def count() -> None:
    return lib.count()
def main() -> int:
    return lib.main()