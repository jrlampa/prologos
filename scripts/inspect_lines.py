import sys
import os

# Obtém o diretório do projeto (assumindo que 'scripts' está um nível abaixo da raiz)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(project_root, "app.py")

with open(path, "rb") as f:
    data = f.read()
lines = data.splitlines()
for idx in range(480, 492):
    if idx - 1 < len(lines):
        print(f"{idx}: {lines[idx-1]!r}")
