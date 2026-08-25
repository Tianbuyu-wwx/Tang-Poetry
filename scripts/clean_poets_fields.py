# -*- coding: utf-8 -*-
"""一次性：对现有 poets-data.js 就地应用 nameEn/dynasty 清洗。

复用 import_docs 的 _clean_name_en / _clean_dynasty，保证与全量重导同规则。
幂等：已干净的值再过一遍函数结果不变。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib import common  # noqa: E402
from import_docs import _clean_name_en, _clean_dynasty  # noqa: E402

POETS_DATA_JS = ROOT / "website" / "assets" / "js" / "poets-data.js"

poets = common.load_js_assignment(POETS_DATA_JS, "POETS_DATA")
fixed_en = fixed_dyn = 0
for slug, poet in poets.items():
    old_en = poet.get("nameEn", "")
    new_en = _clean_name_en(old_en)
    if new_en != old_en:
        poet["nameEn"] = new_en
        fixed_en += 1
    old_dyn = poet.get("dynasty", "")
    new_dyn = _clean_dynasty(poet, poet.get("sub", ""))
    if new_dyn != old_dyn:
        poet["dynasty"] = new_dyn
        fixed_dyn += 1

common.write_js(POETS_DATA_JS, "POETS_DATA", poets)
print(f"nameEn cleaned: {fixed_en}, dynasty cleaned: {fixed_dyn}, total poets: {len(poets)}")
