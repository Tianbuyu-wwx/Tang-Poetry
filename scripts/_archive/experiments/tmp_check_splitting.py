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

CLASSICAL_PREFIXES = [
    "旧唐书","新唐书","北史","南史","晋书","后汉书","汉书","史记","三国志","隋书",
    "周书","梁书","陈书","魏书","北齐书","南齐书","宋书",
    "元和郡县志","水经注","文心雕龙","西京杂记","山海经","淮南子","吕氏春秋",
    "太平御览","艺文类聚","初学记","白孔六帖","玉台新咏","乐府诗集","古诗源",
    "唐诗品汇","沧浪诗话","六一诗话","苕溪渔隐丛话","诗人玉屑","滹南诗话",
    "世说新语","酉阳杂俎","博物志","搜神记",
    "风土记","荆楚岁时记","三秦记","洛阳伽蓝记","穆天子传","战国策","公羊传",
    "谷梁传","左氏传","左传","春秋","论语","孟子","荀子","老子","庄子","列子",
    "韩非子","管子","晏子春秋","墨子","尉缭子","商君书","抱朴子","文子","鹖冠子",
    "文选","尚书","周礼","仪礼","尔雅","说文","诗经","楚辞","易经","书经","礼记",
    "孔子","孟子","荀子","老子","庄子","列子","韩非子","管仲","晏婴",
    "屈原","宋玉","景差","贾谊","枚乘","司马相如","扬雄","班固","张衡",
    "蔡邕","孔融","曹操","曹丕","曹植","王粲","刘桢","阮瑀","徐幹",
    "陈琳","应玚","嵇康","阮籍","山涛","向秀","刘伶","王戎","阮咸",
    "陆机","陆云","潘岳","张协","左思","刘琨","郭璞","孙绰","许询",
    "陶渊明","陶潜","谢灵运","颜延之","鲍照","谢朓","谢惠连","谢庄","沈约","江淹",
    "庾信","徐陵","江总","阴铿","何逊","吴均","呉均","王褒","王融","范云",
    "任昉","丘迟","郦道元","刘勰","钟嵘","萧统","萧纲","萧绎",
    "梁武帝","梁元帝","梁简文帝","陈后主","陈後主",
    "宋之问","沈佺期","王勃","杨炯","卢照邻","骆宾王","陈子昂","杜审言",
    "李峤","苏味道","崔融","上官仪","虞世南","欧阳询","褚遂良","薛稷",
    "太宗皇帝","高宗皇帝","中宗皇帝","玄宗皇帝","武则天","上官婉儿",
    "李白","杜甫","王维","孟浩然","王昌龄","高适","岑参","李颀",
    "崔颢","王之涣","王翰","张说","张九龄","贺知章","包融","张旭",
    "孟郊","贾岛","韩愈","柳宗元","刘禹锡","白居易","元稹","张籍",
    "王建","李绅","杜牧","李商隐","温庭筠","韦庄","司空图","韩偓",
    "罗隐","聂夷中","杜荀鹤","许浑","皮日休","陆龟蒙","僧齐己","齐己",
    "魏明帝","魏文帝","魏武帝","晋武帝","汉武帝","汉文帝","汉景帝","隋炀帝",
    "唐太宗","唐玄宗","汉高祖","秦始皇","楚襄王","鲁哀公","齐桓公","晋文公"
]

STYLE_WORDS = ["诗","赋","文","记","传","序","书","表","铭","箴","诔","碑","论","颂","说","志","注","笺","解","引","辞","曲","调","乐府","语录","纪事","提要","演义","评","谱","纂","钞","略","录","编","选","抄","注疏","正义","集解","章句","音义","释文"]

def semantic_split(text, max_len=38):
    result = []
    i = 0
    while i < len(text):
        if len(text) - i <= max_len:
            result.append(text[i:].strip())
            break
        tail = text[i + max_len - 5:i + max_len + 5]
        cut = max_len
        m = re.search(r'[而以之于则故乃遂因与者也矣焉兮乎哉耶欤](?=[\u4e00-\u9fff])', tail)
        if m:
            cut = max_len - 5 + m.start() + 1
        result.append(text[i:i+cut].strip())
        i += cut
    return [r for r in result if r]

def find_citation_boundaries(text):
    boundaries = [0]
    for prefix in CLASSICAL_PREFIXES:
        plen = len(prefix)
        idx = 0
        while True:
            idx = text.find(prefix, idx)
            if idx == -1:
                break
            if prefix[-1] in STYLE_WORDS:
                boundaries.append(idx)
                idx += 1
                continue
            after = text[idx+plen:idx+plen+10]
            has_style = False
            for w in STYLE_WORDS:
                pos = after.find(w)
                if pos == -1 or pos > 6:
                    continue
                before = after[:pos]
                if re.match(r'^[\u4e00-\u9fff]{0,6}$', before):
                    has_style = True
                    break
            if has_style:
                boundaries.append(idx)
            idx += 1
    boundaries = sorted(set(boundaries))
    return boundaries

def split_annotation_sentences(text):
    output = []
    for part in str(text).split('\n'):
        line = part.strip()
        if not line:
            continue
        for sub in re.split(r' {2,}', line):
            sub = sub.strip()
            if not sub:
                continue
            if re.search(r'[。！？；]', sub):
                for sentence in re.split(r'(?<=[。！？；])', sub):
                    sentence = sentence.strip()
                    if sentence:
                        output.append(sentence)
                continue
            boundaries = find_citation_boundaries(sub)
            if len(boundaries) <= 1:
                output.extend(semantic_split(sub, 38))
                continue
            if boundaries[-1] != len(sub):
                boundaries.append(len(sub))
            for i in range(len(boundaries)-1):
                piece = sub[boundaries[i]:boundaries[i+1]].strip()
                if not piece:
                    continue
                if len(piece) > 42:
                    output.extend(semantic_split(piece, 38))
                else:
                    output.append(piece)
    return output

issues = []
stats = {'total_classical_notes': 0, 'split_notes': 0, 'single_sentence_notes': 0, 'empty_after_split': 0}
for aid, rec in data.items():
    notes = rec[7] if len(rec) > 7 else []
    for note in notes:
        if not isinstance(note, (list, tuple)) or len(note) < 2:
            continue
        term = str(note[0])
        if not re.match(r'^(?:古注|古评|校注)·《', term):
            continue
        stats['total_classical_notes'] += 1
        body = str(note[1])
        sentences = split_annotation_sentences(body)
        if not sentences:
            stats['empty_after_split'] += 1
            issues.append((aid, rec[0], term, 'empty_after_split', body[:80]))
            continue
        if len(sentences) == 1:
            stats['single_sentence_notes'] += 1
        else:
            stats['split_notes'] += 1
        # 检查是否有句子末尾断裂词（如古籍名被截断）
        for s in sentences:
            # 如果某句以常见虚词/介词结尾且不是完整引用，可能断裂
            if len(s) >= 38 and re.search(r'(於|在|以|而|之|其|所|为|因|故|乃|遂|因|与|者|也|矣|焉|兮|乎|哉|耶|欤)$', s):
                issues.append((aid, rec[0], term, 'possible_break', s[:60] + ('...' if len(s)>60 else '')))
                break

print(json.dumps(stats, ensure_ascii=False, indent=2))
print('\nPotential issues (first 20):')
for it in issues[:20]:
    print(it)
print(f'\nTotal issues: {len(issues)}')
