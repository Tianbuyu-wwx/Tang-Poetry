# -*- coding: utf-8 -*-
import json, os
path = r'e:\项目\Tang Poetry\website\assets\js\poems-data.js'
text = open(path, encoding='utf-8').read()
body = text[len('window.POEMS_DATA='):]
if body.endswith(';'):
    body = body[:-1]
D = json.loads(body)
epub = docs = other = 0
for rec in D.values():
    app = rec[8]
    if isinstance(app, dict) and app.get('body'):
        src = app.get('source', '')
        if src:
            epub += 1
        else:
            docs += 1
    elif isinstance(app, str) and app.strip():
        other += 1
print('appreciation with writer source (EPUB-like):', epub)
print('appreciation without source (docs-like):', docs)
print('appreciation plain string:', other)
