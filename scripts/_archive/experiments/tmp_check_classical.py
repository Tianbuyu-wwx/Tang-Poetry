# -*- coding: utf-8 -*-
import json, re
from pathlib import Path

p = Path(r'e:\项目\Tang Poetry\website\assets\js\poems-data.js')
text = p.read_text(encoding='utf-8')
if text.startswith('window.POEMS_DATA='):
    text = text[len('window.POEMS_DATA='):]
if text.endswith(';'):
    text = text[:-1]

data = json.loads(text)
authors = ['李白','杜甫','王维','白居易','李商隐','杜牧','王昌龄','孟浩然','陈子昂','韩愈','刘禹锡','元稹','王之涣','高适','岑参']
results = {}
for aid, rec in data.items():
    author = rec[1] if len(rec) > 1 else ''
    title = rec[0] if len(rec) > 0 else ''
    notes = rec[7] if len(rec) > 8 else []
    has_classical = any(
        isinstance(n, (list, tuple)) and len(n) >= 2 and
        re.match(r'^(?:古注|古评|校注)·《', str(n[0]))
        for n in notes
    )
    if not has_classical:
        continue
    results.setdefault(author, []).append((aid, title))

sample = {}
for a in authors:
    if a in results:
        sample[a] = results[a][:2]

print(json.dumps(sample, ensure_ascii=False, indent=2))
