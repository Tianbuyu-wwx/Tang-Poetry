# 全唐诗静态鉴赏站

这是一个《全唐诗》资料整理与静态展示项目。当前网站收录 57674 首诗、3656 位作者，其中 3743 首带题解、注释、赏析或可核对的古籍注评，另提供 12 部公版唐诗典籍（402 章）全文检索与阅读；558 条名句用于首页展示。

## 直接浏览

网站没有后端依赖。在项目根目录运行：

```powershell
python -m http.server 8000 --directory website
```

然后访问 `http://localhost:8000/`。不建议直接双击 HTML；本地静态服务器的资源加载行为更接近正式部署。

## 目录

- `website/`：可直接部署的静态网站。
- `website/assets/js/`：诗作、检索索引、诗人、名句与典籍数据；页面实际使用轻量索引和按需分片。
- `docs/`：开放《全唐诗》语料、诗人生平、十二部公版典籍、整理文档与资料索引。
- `scripts/crawl/`：原文解析、资料注入和前端数据生成脚本。
- `scripts/data/`：人工整理或按作者拆分的诗作模块。

核心原文来自 `docs/quan_tang_shi_open.json`；诗人生平来自 `docs/quan_tang_shi_poets_biographies.json`，典籍来自 `docs/tang_commentaries_public_domain*`。来源、许可和导入结果详见 `docs/资料索引.md`。当前前端数据以 `website/assets/js/*.js` 为交付物。

## 数据更新

从 `docs/` 统一重建网站数据：

```powershell
python scripts/import_docs.py
python scripts/crawl/build_poems_index.py
python scripts/verify_all.py
node scripts/verify_frontend.js
```

导入脚本会统一繁简、归并作者、迁移现有注解，并用相邻诗句的唯一十字片段把公版古注挂接到具体诗作；无法可靠对齐的内容不会强行写入。脚本同时生成诗作、诗人、典籍、站点统计、`docs/资料索引.md` 和 `docs/典籍注释匹配报告.md`。`scripts/crawl/` 中的历史 `gen_*`、`inject_*` 脚本仍保留，用于追溯旧的分阶段整理流程。

`scripts/import_docs.py` 会自动调用 `scripts/build_frontend_assets.py`，生成诗作分片、诗人作品分片和逐部典籍文件。若只调整了完整数据包，也可以单独运行后者刷新前端分片。

数据转换依赖 `pypinyin` 与 `opencc-python-reimplemented`，见 `requirements.txt`；Windows 环境缺少 OpenCC 时会使用系统繁简映射。项目不包含 OCR 虚拟环境、OCR 依赖、PDF 原件或 OCR 页结果。

## 数据说明

全量覆盖表示原文已收录，并不表示每首诗都有人工注释。网站会通过“注”标识区分已有题解、注释、赏析或古籍注评的诗作；古籍注评保留原文和书名，不冒充现代白话注释。资料仅供学习与赏析使用，引用和再发布时应继续核对各条目的出处与授权条件。
