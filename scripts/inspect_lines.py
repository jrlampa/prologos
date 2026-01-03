import sys

path = r"c:\prologos\app.py"
with open(path, "rb") as f:
    data = f.read()
lines = data.splitlines()
for idx in range(480, 492):
    if idx - 1 < len(lines):
        print(f"{idx}: {lines[idx-1]!r}")
