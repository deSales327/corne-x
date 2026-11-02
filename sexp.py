"""Parser/serializador mínimo de S-expressions do KiCad."""
import re

TOK = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')


def parse(s):
    stack = [[]]
    for t in TOK.findall(s):
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t)
    return stack[0][0]


def find(x, key):
    return [c for c in x if isinstance(c, list) and c and c[0] == key]


def dumps(x, ind=0):
    if not isinstance(x, list):
        return x
    # mantém a ordem original dos elementos (o KiCad depende dela, ex.: "hide")
    if all(not isinstance(c, list) or all(not isinstance(d, list) for d in c) for c in x):
        return '(' + ' '.join(dumps(c) for c in x) + ')'
    pad = '  ' * (ind + 1)
    out = '(' + x[0]
    for c in x[1:]:
        out += ('\n' + pad + dumps(c, ind + 1)) if isinstance(c, list) else ' ' + c
    return out + ')'
