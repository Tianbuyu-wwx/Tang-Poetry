import re, sys
path = sys.argv[1] if len(sys.argv)>1 else 'shi.html'
d = open(path, encoding='utf-8', errors='ignore').read()
body = re.sub(r'<script[^>]*>.*?</script>', '', d, flags=re.S)
body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.S)
for kw in ['行路难','金樽清酒','注释','译文','赏析','创作','背景','作者简介']:
    i = body.find(kw)
    print(f"[{kw}] idx={i}")
text = re.sub(r'<[^>]+>', ' ', body)
text = re.sub(r'\s+', ' ', text)
print("=== visible text (first 2500) ===")
print(text[:2500])
