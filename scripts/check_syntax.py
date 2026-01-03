import sys

source = open(r"c:\prologos\app.py", "r", encoding="utf-8").read()
try:
    compile(source, r"c:\prologos\app.py", "exec")
    print("compile ok")
except SyntaxError as e:
    print("SyntaxError:", e)
    lines = source.splitlines()
    lno = e.lineno
    start = max(0, lno - 5)
    end = min(len(lines), lno + 5)
    print("\nContext:")
    for i in range(start, end):
        print(f"{i+1}: {lines[i]}")
    sys.exit(1)
