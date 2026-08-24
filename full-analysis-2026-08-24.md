# 石湖诗社静态站 · 优化评估报告

日期：2026-08-24 ｜ 对象：`E:\项目\Tang Poetry`（main @ 4ec270e）
方法：全量文件清点 + 构建链实跑（verify_all.py）+ 线上探测 + 结构探针扫描

---

## 一、总体判断

**架构选型是对的，且执行质量高。** 57,676 首诗的站点没有掉进「每诗一个 HTML」的坑，而是单模板 + 数据分片按需加载；构建链 74 项校验全绿；CI 从源重建不回写产物的决策有实测数据支撑。当前的问题不在「能不能跑」，而集中在四件事：**SEO 几乎为零、投稿闭环有一个必坏配置、仓库体积失控趋势、缓存版本号靠手工维护**。

综合评分：

| 维度 | 评分 | 一句话 |
|---|---|---|
| 架构设计 | ⭐⭐⭐⭐⭐ | 分片懒加载 + SW 离线 + CMS 投稿，超出同类业余项目水准 |
| 构建/校验链 | ⭐⭐⭐⭐⭐ | 74 项检查全绿，幂等，CI 设计成熟 |
| 性能 | ⭐⭐⭐⭐ | 首屏轻；扣分在 poets-index 660KB、检索页 5.3MB 一次性加载 |
| SEO/可发现性 | ⭐ | 无 robots/sitemap/canonical/静态 meta，5.7 万页内容对外不可见 |
| 工程卫生 | ⭐⭐⭐ | 追踪体积 265MB 且有继续膨胀机制；版本号 v=13/v=14 手工漂移 |
| 功能完整性 | ⭐⭐⭐⭐ | CMS 后台、体检报告、离线缓存都有；差一处分支配置 |

---

## 二、实测数据

### 规模
- 诗作 57,676 首 / 诗人 3,658 / 典籍 19 部 505 章 / 带注解 5,870 首（site-meta.js）
- 页面 13 个 HTML，全部动态渲染；核心页面 JS 共 ~120KB
- 校验链：`verify_all.py` 74 项 [OK]，0 fail（本次实跑）
- 线上 `tianbuyu-wwx.github.io/Tang-Poetry/` 存活（HTTP 200）

### 体积（git 追踪，共 265.5 MB / 3,103 文件）
| 文件 | 大小 | 说明 |
|---|---|---|
| docs/quan_tang_shi_poets_biographies.json | 41.2 MB | 源数据 |
| scripts/_work/poems-data.js | 29.8 MB | **单行**主数据，每次变更压出 ~11MB 新 blob |
| scripts/crawl/*.json/txt | ~49 MB | 抓取原料（all_tang_poems 14.1 + qts_all 13.3 + qts_caoyin 8.2 …） |
| website/assets/js/sources-data.js | 13.3 MB | **疑似孤儿产物：全站零引用**（见 P2-1） |
| scripts/_archive/ | 2,707 个文件 | 历史脚本全部入库 |
| .git/ | 96 MB | 历史膨胀中 |

### 站点产物（website/，~90 MB）
- poem-shards 118 个共 30MB：p50 224KB / p95 450KB / **max 1.25MB（open-021）**
- poems-index.js 5.3MB（检索页一次性 defer 加载）
- source-books/ 18 书共 ~15MB（按书懒加载 ✓）

### SEO 现状（逐项核实）
| 项 | 状态 |
|---|---|
| robots.txt | ❌ 404（线上已验证） |
| sitemap.xml | ❌ 404（线上已验证） |
| 静态 description / OG / canonical | ❌ 除 society.html 外全站为 0 |
| JSON-LD 结构化数据 | ❌ 0 |
| 动态 meta（poem 页 JS 注入 OG/description） | ✓ 有，但爬虫不执行 JS 时拿不到 |
| 首页 `<title>` | 「石湖诗社」四个字，无关键词 |

### 其他实测
- 字体：Google Fonts render-blocking（Noto Serif SC 等 3 族）；**fonts.googleapis.com 在中国大陆不可达**，目标读者是中文诗社时这是实际的首屏风险
- Service Worker v6：预缓存 13 页 + Stale-While-Revalidate，设计良好；但资源更新同时依赖 `?v=N` 手工版本号
- **版本号已漂移**：lessons/news/periodicals/society 四页用 `v=14`，其余八页用 `v=13`
- web-vitals.js 只 `console.log`，无任何上报出口
- 404.html 不存在（GitHub Pages 约定读根路径 404.html）
- CMS 后台 `config.yml`：`backend.branch: master`，**仓库实际分支是 `main`**

---

## 三、问题清单（P0–P3）

### P0 —— 阻断性

**P0-1 投稿后台线上必坏：CMS 目标分支不存在**
- 证据：`website/admin/config.yml` → `backend: { name: github, repo: your-org/shihu-poetry, branch: master }`
- `.github/workflows/deploy.yml` 的「注入仓库信息」步骤只 sed 替换了 repo 占位符，**没替换 branch**
- 后果：社员打开 /admin/ 登录后，所有保存动作都会指向不存在的 `master` 分支，投稿闭环整体失效
- 修法（二选一）：config 改 `branch: main`；或 deploy.yml 注入步骤追加 `sed -i "s|branch: master|branch: ${GITHUB_REF_NAME}|"`

### P1 —— 重大

**P1-1 SEO 全缺：5.7 万页内容对外不可见**
一个以内容为核心的鉴赏站，目前搜索引擎只能收录 13 个空壳 HTML 的 title。无 sitemap、无 canonical、无静态摘要。百度基本无望（JS 渲染弱），Google 能渲染 JS 但没有 sitemap 和 canonical 辅助，收录效率低。这是当前**价值漏损最大**的一项。

**P1-2 仓库体积失控机制仍在运转**
265MB 已追踪 + `_work/poems-data.js` 单行 29.8MB。文档里的对策（CI 不回写产物）只防住了「投稿频次」这一条增长线，但主数据本身每演进一次（如未来再加批注源）就是一次 11MB blob。crawl 原料 49MB 和 _archive 2,707 个文件属于纯历史包袱。照此趋势，一年内克隆体验会明显恶化。

**P1-3 缓存版本号手工漂移（v=13 vs v=14）**
SW 的 Stale-While-Revalidate 会先返回旧缓存，页面刷新后才能拿到新资源；跨页面引用不同 `?v=` 时，会出现「新 HTML + 旧 CSS」或反向的组合，样式错乱且难复现。现在已经有 4 页与其余 8 页不一致，说明纯手工维护已经失守。

### P2 —— 质量

**P2-1 疑似孤儿产物 sources-data.js（13.3MB）**
全站 HTML/JS 零引用（grep 实证），verify_all.py 还专门断言了「典籍页使用轻量索引与按书分片」。大概率是分片改造前的遗留物，占部署体积 15%。**删除前需跑一次完整构建链确认它不是 build_frontend_assets.py 的必要中间产物。**

**P2-2 Google Fonts 在大陆不可达 + render-blocking**
三族字体阻塞首屏渲染，且目标用户（国内诗社成员）大概率直连超时。建议：pyftsubset 子集化（诗词常用字 3,500~7,000 字）自托管 woff2 + `font-display: swap`，总量可控制在 1~2MB 内并进 SW 预缓存。

**P2-3 检索页一次性加载 5.3MB 索引**
navigation.html defer 加载全量 poems-index.js（gzip 后仍 ~1.5MB），移动端弱网下首次检索等待明显。可拆两级（首字/拼音粗索引 → 细分片）或落 IndexedDB。

**P2-4 poets-index.js 660KB 用于每个 poem 页**
poem.html 只需要「诗人名 → slug/id」映射来渲染面包屑和侧栏，却拉了全量 660KB 索引。可生成一份瘦身的 name→id 映射（预计 <80KB）供详情页专用。

**P2-5 web-vitals 无处可去**
指标只打到 console。接一个免费观测端（Cloudflare Web Analytics / umami 自托管）即可获得真实用户性能画像，否则后续所有性能优化都没有前后对比依据。

**P2-6 无 404 页**
动态路由（?id=xxx）配静态托管，失效链接直接白屏 GitHub 默认 404。补一个风格一致的 404.html 成本极低。

### P3 —— 远期
- JSON-LD（`Poem`/`Article` schema）→ 搜索富摘要
- HTML 内 URL query 的裸 `&` 规范化为 `&amp;`（探针扫出 44 处，实践中无害）
- 外部投稿者 open authoring 权限模型（当前 config 未开启，外部人无法经 CMS 投稿）
- Lighthouse CI 接入 verify.yml，把性能/SEO 变成门禁
- OG 分享卡图自动生成（至少覆盖 916 首带赏析的诗）

> 说明：结构探针报的 31 个「broken internal hrefs」经逐一核查全部为误报（`?v=13` 查询串和 JS 模板字符串不被探针识别），不计入问题。

---

## 四、优化路线图

### 第一批 · 快赢（合计约半天，互不依赖）
1. **P0-1**：修 CMS 分支（1 行 config 或 1 行 sed）
2. **P1-1a**：构建链新增 sitemap 生成（sitemap index + ≤5 万 URL 分片，纯文本成本可忽略）+ robots.txt
3. **P1-3**：版本号自动化——build 时统一改写全部 HTML 的 `?v=`（单一来源 site-meta），消灭手工漂移
4. **P2-6**：404.html
5. **P2-1**：跑一遍干净构建验证 sources-data.js 可去后，从生成清单剔除（-13.3MB）

### 第二批 · 中期（1~2 周）
6. **P1-1b**：全站静态 meta 补齐（description/OG/canonical）+ poem 页 JSON-LD；title 加关键词
7. **P2-2**：字体子集化自托管
8. **P2-4**：详情页专用瘦身诗人映射
9. **P2-5**：web-vitals 接上报端
10. **P1-2 第一刀**：crawl 原料 + _archive 移出 git（挪到本地归档目录或 Release 附件，仓库瘦身 ~85MB）

### 第三批 · 需要拍板的架构决策
11. `_work/poems-data.js` 出库方案三选一：
    - A. 维持现状（接受偶发 11MB blob，胜在简单）
    - B. 移到 GitHub Release 附件，构建时下载（仓库最瘦，多一步网络依赖）
    - C. Git LFS（克隆体验折中，Pages/CI 均兼容）
12. docs/ 下 41MB+18MB 大 JSON 是否同样外移
13. `.git` 历史 96MB 是否做 filter-repo 重写（破坏性操作，需全员协调，当前只有你一个贡献者所以窗口合适）

---

## 五、结语
这个项目的底子足以支撑它走很远；当前最划算的投入顺序是 **P0-1 → SEO 基础件 → 版本号自动化 → 仓库瘦身**。前三项都是小时级工作量，收益立竿见影。
