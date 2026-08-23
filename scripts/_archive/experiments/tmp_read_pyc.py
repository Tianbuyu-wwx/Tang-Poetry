# -*- coding: utf-8 -*-
import marshal, types, sys, json

path = sys.argv[1]
with open(path, 'rb') as f:
    f.read(16)
    code = marshal.load(f)

samples = []

def scan(obj, depth=0):
    if depth > 6:
        return
    if isinstance(obj, types.CodeType):
        for c in obj.co_consts:
            scan(c, depth+1)
    elif isinstance(obj, (list, tuple)):
        if len(obj) > 0:
            sample = obj[:2]
            samples.append((kind := 'tuple' if isinstance(obj, tuple) else 'list', len(obj), [type(x).__name__ for x in sample], sample))
        for item in obj[:3]:
            scan(item, depth+1)
    elif isinstance(obj, dict) and obj:
        samples.append(('dict', len(obj), list(obj.keys())[:5], None))

scan(code)
for s in samples[:20]:
    print(s)
