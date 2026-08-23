# 部署与 CI 说明

本文说明石湖诗社站点的自动构建、投稿校验与上线机制。面向社务管理者与后续维护者。

当前采用的运行模式：**本地模式**（投稿后台跑在本机，站点尚未接入线上托管）。
`.github/workflows/` 下的两个工作流已就绪并通过验证，一旦仓库推上 GitHub 即自动生效，无需改动。

---

## 一、核心契约：谁是事实源

| 内容 | 事实源 | 说明 |
| --- | --- | --- |
| 社员作品、社员档案 | `docs/curated/` | **唯一事实源**，投稿后台读写的就是这里 |
| 经典库（全唐诗、古典补遗） | `scripts/_work/poems-data.js` | 构建期主数据，已入库 |
| 网站产物 | `website/` | 由构建生成；**仓库里的副本仅供本地预览，可能落后于线上** |
| 作品编号 | `docs/curated/poem-ids.json` | 链接稳定性的唯一凭据，**由脚本维护，勿手改** |

线上以 CI 的构建结果为准。改内容只改 `docs/`，不要手改 `website/` 里的生成文件。

### 为什么 CI 不把产物回写仓库

实测数据支撑这个决策：

- 全量重建耗时 **2.3 ～ 3.5 秒**，且完全确定性（同输入重跑后 `git status` 零 diff）。
- 主数据 `scripts/_work/poems-data.js` 是 **29.8 MB 的单行 JS**。单行意味着改一个字符整个文件就算全变，每回写一次就在仓库里压出一个约 **11.1 MB** 的新 blob。
- 按投稿频次累计，仓库会迅速膨胀到无法克隆。

既然重建只要几秒，就没有理由为它付 11 MB 的存储代价。**唯一必须持久化的是几百字节的 `poem-ids.json`**——丢了它，新投稿会挤掉既有作品的编号，已经分享出去的链接全部失效。

需要让仓库产物与线上对齐时（例如要做本地预览），手动触发 `构建并部署` 工作流并勾选 `sync_artifacts` 即可，属于例外操作。

---

## 二、两个工作流

### 1. `投稿校验`（`.github/workflows/verify.yml`）

**触发**：任何改动 `docs/` `website/` `scripts/` `requirements*.txt` 的 Pull Request。

**只读不写**——不回写仓库、不部署，产物全部留在 runner 上。

步骤：

1. 检出源码（`fetch-depth: 0`，体检报告需要与基线分支比对，浅克隆拿不到 merge base）
2. 装 Python 3.13 + Node 22，只装 `requirements-build.txt`（唯一第三方依赖 `pyyaml`）
3. 重建社库 `build_curated.py`
4. 数据校验门 `verify_all.py`
5. 脚本解析门 `verify_frontend.js`
6. **生成投稿体检报告**并贴回 PR（sticky 评论，重复推送只更新同一条，不刷屏）

第 6 步用 `if: always()`——构建失败时照样出报告，因为投稿人最需要知道的恰恰是哪一步不合规。

### 2. `构建并部署`（`.github/workflows/deploy.yml`）

**触发**：推送到 `main` 或 `master`（两者都监听，避免改名或迁移后工作流静默失效）；也可手动触发。

步骤：

1. 重建 + 双校验门（同上）
2. **持久化编号注册表**：`poem-ids.json` 有变才提交（`[skip ci]` 避免递归触发），推送前 `git pull --rebase --autostash` 防止与并发合并撞车
3. *（可选）* 手动触发且勾选 `sync_artifacts` 时，才回写 `website/` 与 `scripts/_work/` 产物
4. **注入仓库信息**：把 `website/admin/config.yml` 里的占位符 `your-org/shihu-poetry` 替换成 `${GITHUB_REPOSITORY}`。源码保持占位符，产物按当前仓库自动落名——fork 或改名都不用手改配置
5. 打包 `website/` 上传为 Pages artifact 并部署

并发控制用 `concurrency: pages` 且 `cancel-in-progress: false`，保证部署串行，避免两次合并同时上线导致后发先至。

---

## 三、投稿体检报告

`scripts/review_submission.py` 把稿件翻译成人话，让审稿人不必去读 diff 里的 YAML。

```bash
# 与基线分支比对（CI 用法）
python scripts/review_submission.py --base origin/master --output review.md

# 检查指定文件
python scripts/review_submission.py --files docs/curated/poems/xxx.md

# 全量体检（盘点现有社库）
python scripts/review_submission.py --all
```

报告内容：

- **字段完整度**：题解、注释、赏析、名句、出处是否齐备（缺失只提示，不拦截——可先上站后补）
- **作者是否在册**：核对 `docs/curated/members/` 名录，不在册会警告
- **分配到的编号与上站地址**：例如 `member_3` → `poem.html?id=member_3`
- **格律形制校验**：按体裁核对句数与字数

### 关于形制校验的一个要点

统计**按句**（标点切分）而非按行。旧体诗的书写惯例是**一联一行**，所以一首八句五律通常只占 4 行——按行统计会把正确的稿子误判为错误。

实测有效：把一首五言四句标成「七绝」，报告会准确指出「七绝应每句 7 字，实际 5 字」。

---

## 四、本地模式怎么用（当前采用）

无需 GitHub、无需 OAuth，全流程在本机跑通：

```bash
# 终端 1：启动 Decap 的本地代理（直接读写工作区文件）
npx decap-server

# 终端 2：起静态服务器
python -m http.server 8931 -d website
```

浏览器打开 `http://localhost:8931/admin/`，会自动进入本地模式（`config.yml` 里已开 `local_backend`）。填表保存后改动直接落到 `docs/curated/`。

> **注意**：本地模式**不支持 `editorial_workflow`**，后台不会出现「工作流」看板，保存即落盘、没有审核环节。这是官方限制——本地代理只报告 `publish_modes: ["simple"]`，Decap 自动降级。接入 GitHub 后端后审核流程会自动恢复，配置无需改动。详见 `docs/投稿后台使用说明.md` 第五节。

写完后重建看效果：

```bash
python scripts/build_curated.py
python scripts/verify_all.py
node scripts/verify_frontend.js
```

Windows 上请用托管 venv 的解释器：
`C:\Users\<用户名>\.workbuddy\binaries\python\envs\default\Scripts\python.exe`

---

## 五、将来接线上时要做的事

按顺序：

1. **建 GitHub 仓库并推送**——工作流随代码一起上去，立即生效。
2. **开启 Pages**：仓库 Settings → Pages → Source 选 **GitHub Actions**（不要选 Deploy from a branch）。
3. **确认 Actions 写权限**：Settings → Actions → General → Workflow permissions 选 **Read and write**，否则第 2 步的编号注册表持久化会失败。
4. **配 OAuth 中转**（Decap 的 GitHub 后端需要，纯静态托管不自带）。三选一：
   - **Netlify**：用内置 Identity + Git Gateway，不用自己搭中转，配置最少。
   - **Cloudflare Pages + Worker**：自建一个极简 Worker 做 OAuth 中转，长期成本最低、国内访问较快。
   - **GitHub Pages + 官方 oauth-provider**：全在 GitHub 生态内，但中转服务要自己找地方常驻。
5. 选定后把 `website/admin/config.yml` 的 `backend` 段按所选方案调整；`repo` 字段不用管，部署时会自动注入。

---

## 六、依赖与环境

`requirements-build.txt` 是 CI 的最小依赖集，只有 `pyyaml`——构建与校验链路的唯一第三方依赖。

`requirements.txt` 引用它，再叠加历史数据转换脚本才需要的 `pypinyin`、`opencc`。日常构建不需要后两者。

构建链路无 Windows 特定代码（无 `ctypes`/`winreg`/路径分隔符假设），Linux runner 可直接跑。已用 `git worktree` 建纯净检出实测：从零检出到双校验门全绿，全链路 2.3 秒。
