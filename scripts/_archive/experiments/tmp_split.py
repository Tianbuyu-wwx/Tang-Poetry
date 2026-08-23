import json, re, os, random, sys

STYLE_WORDS = '诗|赋|文|记|传|序|书|表|铭|箴|诔|碑|论|颂|说|志|注|笺|解|引|辞|曲|调|乐府|语录|纪事|提要|集|演义|评|谱|纂|钞|略|录|编|钞|选|抄|注疏|正义|集解|章句|音义|释文'
BOUNDARY_RE = re.compile(r'[\u4e00-\u9fff]{2,8}(?:' + STYLE_WORDS + r')')

def split_classical(text, max_len=42):
    text = text.strip()
    if not text:
        return []
    if re.search(r'[。！？；]', text):
        parts = re.split(r'(?<=[。！？；])', text)
        return [p.strip() for p in parts if p.strip()]
    markers = [(m.start(), m.end()) for m in BOUNDARY_RE.finditer(text)]
    if len(markers) <= 1:
        return semantic_split(text, max_len)
    pieces = []
    for i, (start, end) in enumerate(markers):
        next_start = markers[i+1][0] if i+1 < len(markers) else len(text)
        piece = text[start:next_start].strip()
        if piece:
            pieces.append(piece)
    if markers[0][0] > 0:
        prefix = text[:markers[0][0]].strip()
        if prefix:
            pieces[0] = prefix + pieces[0]
    result = []
    for p in pieces:
        if len(p) > max_len:
            result.extend(semantic_split(p, max_len))
        else:
            result.append(p)
    return result

def semantic_split(text, max_len=42):
    parts = re.split(r'(又[，、]?)', text)
    merged = []
    i = 0
    while i < len(parts):
        if parts[i] in ('又', '又，', '又、'):
            if i+1 < len(parts):
                merged.append(parts[i] + parts[i+1])
                i += 2
            else:
                merged.append(parts[i])
                i += 1
        else:
            merged.append(parts[i])
            i += 1
    merged = [p.strip() for p in merged if p.strip()]
    result = []
    for p in merged:
        if len(p) <= max_len:
            result.append(p)
            continue
        while len(p) > max_len:
            tail = p[max_len-5:max_len+5]
            m = re.search(r'[而以之于则故乃遂因与者也矣焉兮乎哉耶欤](?=[\u4e00-\u9fff])', tail)
            if m:
                cut = max_len - 5 + m.end()
            else:
                cut = max_len
            result.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            result.append(p)
    return result

samples = [
    "傅咸喜雨诗灵岳兴庆云之飘颻陶潜归去来辞云无心以出岫谢朓诗𥦗中列逺岫呉均诗轻云纫逺岫细雨沐单衣",
    "西京杂记淮南方士有嘘吸为寒暑喷𠻳为雨雾鲍照河清颂长河巨济异源同清",
    "贾岛诗洞庭风落水天姥月离云梁简文帝乐府客行祗念路相争度京口元和郡县志润州本春秋呉子朱方邑始皇改为丹阳汉初为荆国建安十四年孙权自呉理丹徒号曰京城十六年迁都建业於此为京口唐书地理志开元二十年刺史齐澣以舟行绕𤓰歩囘逺六十里多风涛乃於京口埭下直趋渡江舟不飘没谢朓诗天际识归舟云中辨江树",
    "史记曹相国世家参告舍人趣治行吾将入相张九龄诗戒程有攸徃罗邺诗络日长程绕短程",
    "文心雕龙搜句忌于颠倒",
    "吉若济巨川用汝作舟楫易利涉大川庄子冯夷得之以游大川沈佺期诗积气冲长岛浮光溢大川",
]

out = []
for s in samples:
    out.append('---')
    out.append('原文: ' + s)
    out.append('切分:')
    for i, p in enumerate(split_classical(s), 1):
        out.append(f'  {i}. {p} ({len(p)}字)')
with open('tmp_split_out.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('done')
