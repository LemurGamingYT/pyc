def count() -> None:
    i = 0
    while i < 1_000_000_000:
        i = i + 1

def main() -> int:
    count()
    return 0
