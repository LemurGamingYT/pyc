def fib_recursive(n: int) -> int:
    if n <= 1:
        return n

    return fib_recursive(n - 1) + fib_recursive(n - 2)

def fib() -> int:
    return fib_recursive(35)

def main() -> int:
    return 0
