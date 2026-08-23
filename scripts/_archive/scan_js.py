# -*- coding: utf-8 -*-
import re
p = r'e:\项目\Tang Poetry\website\assets\js\poets-data.js'
s = open(p, encoding='utf-8').read()
# 找 ASCII 双引号紧贴中文字符的位置
pat = re.compile(r'[\u4e00-\u9fff]"|"[\\u4e00-\u9fff]')
for m in pat.finditer(s):
    start = max(0, m.start() - 30)
    end = min(len(s), m.end() + 30)
    print(repr(s[start:end]))
    print('---')
