# -*- coding: utf-8 -*-
import json, os
path = r'e:\项目\Tang Poetry\website\assets\js\poems-data.js'
text = open(path, encoding='utf-8').read()
body = text[len('window.POEMS_DATA='):]
if body.endswith(';'):
    body = body[:-1]
D = json.loads(body)
total = len(D)
has_app = has_note = has_tijie = has_any = 0
for rec in D.values():
    app = rec[8]
    app_ok = False
    if isinstance(app, dict) and app.get('body') and any(str(x).strip() for x in app['body']):
        app_ok = True
    elif isinstance(app, str) and app.strip():
        app_ok = True
    note_ok = bool(rec[7] and any(str(x).strip() for sub in rec[7] for x in (sub if isinstance(sub, (list, tuple)) else [sub])))
    tijie_ok = bool(str(rec[6] or '').strip())
    if app_ok:
        has_app += 1
    if note_ok:
        has_note += 1
    if tijie_ok:
        has_tijie += 1
    if app_ok or note_ok or tijie_ok:
        has_any += 1
print('total', total)
print('has_appreciation', has_app)
print('has_notes', has_note)
print('has_tijie', has_tijie)
print('has_any', has_any)
