# -*- coding: utf-8 -*-
"""修复 poets-data.js 中字符串字面量内部误用的 ASCII 双引号。
逻辑：扫描每一行，在 "..." 字符串内部遇到 " 时，
若其后紧跟 ,)]}: 或行尾，视为字符串结束；
否则视为内嵌引号，按左右配对替换为中文 “ ”。
单引号字符串、注释（// 和 /* */）跳过。
"""
import re

src_path = r'e:\项目\Tang Poetry\website\assets\js\poets-data.js'
text = open(src_path, encoding='utf-8').read()
lines = text.splitlines(keepends=True)

END_FOLLOW = set(',)]};') | {'\n', '\r', '+'}

def fix_line(line: str) -> str:
    out = []
    i = 0
    n = len(line)
    in_str = False
    quote = None
    buf = []
    inner_open = True
    while i < n:
        ch = line[i]
        if not in_str:
            # 检查注释 //...
            if ch == '/' and i + 1 < n and line[i+1] == '/':
                out.append(line[i:])
                break
            # 检查注释 /*...*/ （单行情况）
            if ch == '/' and i + 1 < n and line[i+1] == '*':
                # 找到 */
                end_idx = line.find('*/', i+2)
                if end_idx == -1:
                    out.append(line[i:])
                    break
                out.append(line[i:end_idx+2])
                i = end_idx + 2
                continue
            if ch == '"' or ch == "'":
                in_str = True
                quote = ch
                buf = [ch]
                inner_open = True
                i += 1
                continue
            out.append(ch)
            i += 1
            continue
        # 在字符串内
        if ch == '\\':
            buf.append(ch)
            if i + 1 < n:
                buf.append(line[i+1])
                i += 2
            else:
                i += 1
            continue
        if ch == quote:
            # 判断是否结束
            j = i + 1
            while j < n and line[j] in ' \t':
                j += 1
            next_ch = line[j] if j < n else '\n'
            if next_ch in END_FOLLOW:
                # 字符串结束
                buf.append(ch)
                out.append(''.join(buf))
                buf = []
                in_str = False
                quote = None
                inner_open = True
                i += 1
                continue
            else:
                # 误嵌入：仅对双引号字符串做替换；单引号字符串保留原样（需转义）
                if quote == '"':
                    buf.append('\u201c' if inner_open else '\u201d')
                    inner_open = not inner_open
                else:
                    # 单引号字符串内出现单引号——保留并转义
                    buf.append('\\' + ch)
                i += 1
                continue
        buf.append(ch)
        i += 1
    if buf:
        out.append(''.join(buf))
    return ''.join(out)


new_lines = []
replaced_total = 0
for line in lines:
    if line.count('"') > 2:
        new_line = fix_line(line)
        replaced_total += line.count('"') - new_line.count('"')
        new_lines.append(new_line)
    else:
        new_lines.append(line)

open(src_path, 'w', encoding='utf-8').write(''.join(new_lines))
print(f'已替换 {replaced_total} 个内嵌 ASCII 引号为中文引号')
