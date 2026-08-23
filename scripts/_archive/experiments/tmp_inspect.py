import json, re
with open('website/assets/js/poem-shards/open-000.js', 'r', encoding='utf-8') as f:
    text = f.read()
m = re.search(r'window\.POEM_SHARD\s*=\s*(\{.*?\});\s*$', text, re.DOTALL)
if not m:
    print('未找到 POEM_SHARD')
    exit(1)
data = json.loads(m.group(1))
rec = data.get('open_00045')
if not rec:
    print('未找到 open_00045')
    exit(1)
out = []
out.append('诗题: ' + rec[0])
out.append('作者: ' + rec[1])
out.append('notes 数量: ' + str(len(rec[7])))
for i, note in enumerate(rec[7][:8]):
    out.append('\n--- note ' + str(i) + ' ---')
    out.append('term: ' + note[0])
    out.append('body: ' + note[1][:600])
with open('tmp_inspect_out.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('已写入 tmp_inspect_out.txt')
