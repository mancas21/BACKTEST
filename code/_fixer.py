import os
for p in [r"C:\Users\Lenovo\Documents\backtest-system\code\_nt_smoke.py", r"C:\Users\Lenovo\Documents\backtest-system\code\_trim.py"]:
    b = open(p, "rb").read()
    if b.endswith(b"'") or b.endswith(b"'\\n") or b.endswith(b"'\n"):
        b = b.rstrip(b"'").rstrip(b"\n") + b"\n"
    open(p, "wb").write(b)
    print("fixed", p, len(b))
'