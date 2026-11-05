p = r"C:\Users\Lenovo\Documents\backtest-system\code\survivors_strategy.py"
b = open(p, "rb").read()
# strip trailing single quote and any trailing whitespace/newlines, then add one newline
while b.endswith(b"'") or b.endswith(b"\n") or b.endswith(b"\r"):
    b = b[:-1]
b = b + b"\n"
open(p, "wb").write(b)
print("fixed, size", len(b))