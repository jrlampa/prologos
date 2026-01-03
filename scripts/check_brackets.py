from collections import deque

s = open(r"c:\prologos\app.py", "r", encoding="utf-8").read()
stack = deque()
pairs = {")": "(", "]": "[", "}": "{"}
openers = set(pairs.values())
for i, ch in enumerate(s):
    if ch in "([{":
        stack.append((ch, i))
    elif ch in ")]}":
        if not stack:
            print("Unmatched closer", ch, "at pos", i)
            break
        top, pos = stack.pop()
        if top != pairs[ch]:
            print("Mismatched pair", top, "vs", ch, "at pos", i)
            break
else:
    if stack:
        print("Unmatched opener at pos", stack[-1])
    else:
        print("All brackets balanced")
