from ctypes import CDLL

lib = CDLL('C:/Programming/Python/pyc/examples/test1.dll')

def fib_recursive(n: int) -> int:
    return lib.fib_recursive(n)

def fib() -> int:
    return lib.fib()

def main() -> int:
    return lib.main()
