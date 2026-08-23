"""盘点现有诗作数据，检查重复，输出诗人/诗作统计。"""
import importlib.util
import os
import sys
from collections import Counter, defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_module(path):
    spec = importlib.util.spec_from_file_location('m', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def main():
    poems = []
    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith('.py') and f.startswith('poems_'))
    for f in files:
        m = load_module(os.path.join(DATA_DIR, f))
        if hasattr(m, 'POEMS_LOCAL'):
            for p in m.POEMS_LOCAL:
                p['_source_file'] = f
                poems.append(p)
    print(f'=== 数据文件: {len(files)} 个 ===')
    for f in files:
        print(f'  {f}')
    print(f'\n=== 总诗作数: {len(poems)} ===')
    
    # 按 id 去重检查
    by_id = defaultdict(list)
    for p in poems:
        by_id[p['id']].append(p['_source_file'])
    dups = {k: v for k, v in by_id.items() if len(v) > 1}
    print(f'\n=== ID 重复检查 ===')
    if dups:
        print(f'  发现 {len(dups)} 个重复 ID:')
        for k, v in dups.items():
            print(f'    {k}: {v}')
    else:
        print('  无重复 ID')
    
    # 按 title+author 去重检查
    by_title_author = defaultdict(list)
    for p in poems:
        key = (p['title'], p['author'])
        by_title_author[key].append((p['id'], p['_source_file']))
    dups_ta = {k: v for k, v in by_title_author.items() if len(v) > 1}
    print(f'\n=== 同题同作者重复检查 ===')
    if dups_ta:
        print(f'  发现 {len(dups_ta)} 组同题同作者:')
        for k, v in dups_ta.items():
            print(f'    {k}: {v}')
    else:
        print('  无同题同作者重复')
    
    # 诗人统计
    by_poet = defaultdict(int)
    poet_ids = defaultdict(set)
    for p in poems:
        by_poet[p['author']] += 1
        poet_ids[p['author']].add(p['poet_id'])
    print(f'\n=== 诗人统计: {len(by_poet)} 位 ===')
    for author in sorted(by_poet.keys()):
        pids = poet_ids[author]
        pid_str = ','.join(pids) if len(pids) == 1 else f'!!多ID:{pids}'
        print(f'  {author}: {by_poet[author]} 首  [{pid_str}]')
    
    # 体裁统计
    by_genre = Counter(p['genre'] for p in poems)
    print(f'\n=== 体裁统计 ===')
    for g, c in by_genre.most_common():
        print(f'  {g}: {c}')
    
    # 输出所有诗题列表（按诗人排序）
    print(f'\n=== 所有诗作列表（按诗人+体裁）===')
    sorted_poems = sorted(poems, key=lambda p: (p['author'], p['genre'], p['title']))
    for i, p in enumerate(sorted_poems, 1):
        print(f'{i:3d}. [{p["author"]}] {p["title"]} ({p["genre"]}) id={p["id"]}')

if __name__ == '__main__':
    main()
