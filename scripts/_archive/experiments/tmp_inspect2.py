import json, re, os, random
folder = 'website/assets/js/poem-shards'
files = [f for f in os.listdir(folder) if f.endswith('.js')]
random.seed(42)
sample = random.sample(files, min(15, len(files)))
samples = []
for fn in sample:
    path = os.path.join(folder, fn)
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'window\.POEM_SHARD\s*=\s*(\{.*?\});\s*$', text, re.DOTALL)
    if not m: continue
    data = json.loads(m.group(1))
    for pid, rec in data.items():
        notes = rec[7] or []
        for note in notes:
            if note[0].startswith('古注'):
                samples.append((fn, pid, note[0], note[1]))
        if len(samples) >= 30:
            break
    if len(samples) >= 30:
        break
out = []
for fn, pid, term, body in samples[:30]:
    out.append(f'--- {fn} / {pid} ---')
    out.append(f'term: {term}')
    out.append(f'body: {body[:400]}')
    out.append('')
with open('tmp_inspect2_out.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('已写入，样本数:', len(samples[:30]))
