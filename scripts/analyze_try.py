import ast

s = open(r"c:\prologos\app.py", "r", encoding="utf-8").read()
mod = ast.parse(s)
for node in ast.walk(mod):
    if isinstance(node, ast.Try):
        print(
            "Try at",
            node.lineno,
            "handlers:",
            len(node.handlers),
            "finalbody:",
            bool(node.finalbody),
        )
