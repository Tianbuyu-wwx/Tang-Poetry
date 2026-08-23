import re

STYLE_WORDS = ["诗","赋","文","记","传","序","书","表","铭","箴","诔","碑","论","颂","说","志","注","笺","解","引","辞","曲","调","乐府","语录","纪事","提要","演义","评","谱","纂","钞","略","录","编","选","抄","注疏","正义","集解","章句","音义","释文"]
STYLE_SET = set(STYLE_WORDS)

CLASSICAL_PREFIXES = [
    # 史书/典籍
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
    # 先秦两汉魏晋作者
    "孔子","孟子","荀子","老子","庄子","列子","韩非子","管仲","晏婴",
    "屈原","宋玉","景差","贾谊","枚乘","司马相如","扬雄","班固","张衡",
    "蔡邕","孔融","曹操","曹丕","曹植","王粲","刘桢","阮瑀","徐幹",
    "陈琳","应玚","嵇康","阮籍","山涛","向秀","刘伶","王戎","阮咸",
    "陆机","陆云","潘岳","张协","左思","刘琨","郭璞","孙绰","许询",
    "陶渊明","陶潜","谢灵运","颜延之","鲍照","谢朓","谢惠连","谢庄","沈约","江淹",
    "庾信","徐陵","江总","阴铿","何逊","吴均","呉均","王褒","王融","范云",
    "任昉","丘迟","郦道元","刘勰","钟嵘","萧统","萧纲","萧绎",
    "梁武帝","梁元帝","梁简文帝","陈后主","陈後主",
    # 唐及后世诗人/文人
    "宋之问","沈佺期","王勃","杨炯","卢照邻","骆宾王","陈子昂","杜审言",
    "李峤","苏味道","崔融","上官仪","虞世南","欧阳询","褚遂良","薛稷",
    "太宗皇帝","高宗皇帝","中宗皇帝","玄宗皇帝","武则天","上官婉儿",
    "李白","杜甫","王维","孟浩然","王昌龄","高适","岑参","李颀",
    "崔颢","王之涣","王翰","张说","张九龄","贺知章","包融","张旭",
    "孟郊","贾岛","韩愈","柳宗元","刘禹锡","白居易","元稹","张籍",
    "王建","李绅","杜牧","李商隐","温庭筠","韦庄","司空图","韩偓",
    "罗隐","聂夷中","杜荀鹤","许浑","皮日休","陆龟蒙","僧齐己","齐己",
    # 常见帝王/人物
    "魏明帝","魏文帝","魏武帝","晋武帝","汉武帝","汉文帝","汉景帝","隋炀帝",
    "唐太宗","唐玄宗","汉高祖","秦始皇","楚襄王","鲁哀公","齐桓公","晋文公",
]

def semantic_split_annotation(text, max_len=38):
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
            cut = max_len - 5 + m.end()
        result.append(text[i:i + cut].strip())
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
            # prefix 本身以文体词结尾，则直接视为边界
            if prefix[-1] in STYLE_SET:
                boundaries.append(idx)
                idx += 1
                continue
            after = text[idx + plen:idx + plen + 10]
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
    return sorted(set(boundaries))

def split_annotation_sentences(text, max_len=38):
    output = []
    for part in text.split("\n"):
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
                output.extend(semantic_split_annotation(sub, max_len))
                continue
            if boundaries[-1] != len(sub):
                boundaries.append(len(sub))
            for i in range(len(boundaries) - 1):
                piece = sub[boundaries[i]:boundaries[i + 1]].strip()
                if not piece:
                    continue
                if len(piece) > 42:
                    output.extend(semantic_split_annotation(piece, max_len))
                else:
                    output.append(piece)
    return output

samples = [
    "傅咸喜雨诗灵岳兴庆云之飘颻陶潜归去来辞云无心以出岫谢朓诗𥦗中列逺岫呉均诗轻云纫逺岫细雨沐单衣",
    "西京杂记淮南方士有嘘吸为寒暑喷𠻳为雨雾鲍照河清颂长河巨济异源同清",
    "贾岛诗洞庭风落水天姥月离云梁简文帝乐府客行祗念路相争度京口元和郡县志润州本春秋呉子朱方邑始皇改为丹阳汉初为荆国建安十四年孙权自呉理丹徒号曰京城十六年迁都建业於此为京口唐书地理志开元二十年刺史齐澣以舟行绕𤓰歩囘逺六十里多风涛乃於京口埭下直趋渡江舟不飘没谢朓诗天际识归舟云中辨江树",
    "史记曹相国世家参告舍人趣治行吾将入相张九龄诗戒程有攸徃罗邺诗络日长程绕短程",
    "文心雕龙搜句忌于颠倒",
    "吉若济巨川用汝作舟楫易利涉大川庄子冯夷得之以游大川沈佺期诗积气冲长岛浮光溢大川",
    "三秦记长安正南秦岭岭根水流为秦川一名樊川魏明帝诗出身秦川爰居伊洛尉缭子天子宅千亩",
    "江总乐府绮殿文雅遒玳筵欢趣宻周礼疏八尺曰寻梁书朱异传金山万丈縁陟未登玉海千寻窥暎不测",
]

out = []
for s in samples:
    out.append('---')
    out.append('原文: ' + s)
    out.append('切分:')
    for i, p in enumerate(split_annotation_sentences(s), 1):
        out.append(f'  {i}. {p} ({len(p)}字)')
with open('tmp_split_js2_out.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('done')
