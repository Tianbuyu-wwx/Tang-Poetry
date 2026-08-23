# 石湖诗社 · 品牌资产协议

> 本文件依据 huashu-design-master skill 品牌资产协议 5 步硬流程生成。
> 由于本项目为古典诗词主题，无现成品牌资产，以"诗的视觉文化"作为品牌资产源头。
> 运行时品牌字符串（站名 / 印章 / 页脚 / OG）的单一数据源为 `assets/js/brand.js`，改品牌只需改那一个文件。

---

## 1. 品牌定位

- **项目名**：石湖诗社
- **核心气质**：古典、沉静、文雅、有书卷气
- **禁忌**：紫渐变、emoji 图标、圆角 + 左 border accent、SVG 画人脸、Inter 做 display font（反 AI slop 规则）
- **可借鉴参考**：故宫博物院数字文物库、中国哲学书电子化计划、中国国家图书馆古籍数字图书馆、台北故宫 OPEN DATA

## 2. 三种候选视觉风格

### 风格 A · 水墨写意 · 宣纸留白（试选诗：李白《将进酒》）

**哲学**：原研哉"白" + 中国水墨"计白当黑"。空白是主角，墨色是节奏。
**情绪**：奔放中见沉静，适合李白之豪迈。

| 资产 | 值 |
|------|-----|
| 背景宣纸色 | `oklch(0.95 0.012 80)` 约 `#faf6ed` |
| 主墨色 | `oklch(0.18 0.015 250)` 约 `#1a1a1a` 偏冷 |
| 浓墨 | `oklch(0.08 0.02 250)` 约 `#0a0a0a` |
| 淡墨 | `oklch(0.55 0.01 250)` 约 `#7a7a7a` |
| 印泥朱砂 | `oklch(0.55 0.18 28)` 约 `#a83232` |
| 副印泥 | `oklch(0.42 0.15 25)` 约 `#7a2828` |
| 字体栈（display） | `"STKaiti", "KaiTi", "楷体", "Noto Serif SC", serif` |
| 字体栈（body） | `"STSong", "SimSun", "宋体", "Noto Serif SC", serif` |
| 字体栈（small） | `"STFangsong", "仿宋", "FangSong", serif` |
| 留白比例 | 1.618 黄金分割 |
| 装饰元素 | 朱砂方印、墨痕渲染（CSS gradient 模拟）、轻微 paper noise |

### 风格 B · 工笔绢帛 · 古卷厚重（试选诗：王维《鹿柴》）

**哲学**：宋徽宗瘦金体 + 工笔重彩绢本。绢之温润、金之精微。
**情绪**：禅意中见精细，适合王维之空灵。

| 资产 | 值 |
|------|-----|
| 绢底色 | `oklch(0.89 0.035 75)` 约 `#e8d9b0` |
| 深绢 | `oklch(0.78 0.04 70)` 约 `#c9b582` |
| 主墨色 | `oklch(0.22 0.02 50)` 约 `#3a3024` |
| 描金 | `oklch(0.72 0.12 85)` 约 `#b8945a` |
| 朱砂印 | `oklch(0.50 0.18 28)` 约 `#9c2828` |
| 字体栈（display） | `"STKaiti", "KaiTi", "楷体", serif` |
| 字体栈（body） | `"STSong", "SimSun", "宋体", serif` |
| 装饰元素 | 极细金线分隔、卷轴边缘渐变、双线边框 |

### 风格 C · 竹简古卷 · 简牍风（试选诗：杜甫《春望》）

**哲学**：汉简 + 战国楚简。竖排刻字，沧桑肌理。
**情绪**：沉郁中见古质，适合杜甫之沉郁顿挫。

| 资产 | 值 |
|------|-----|
| 简牍底色 | `oklch(0.65 0.05 75)` 约 `#a8895a` |
| 深简 | `oklch(0.45 0.06 70)` 约 `#7a5e35` |
| 简缝色 | `oklch(0.30 0.04 70)` 约 `#4a3a20` |
| 墨字色 | `oklch(0.10 0.02 50)` 约 `#1a1208` |
| 朱砂栏 | `oklch(0.45 0.18 30)` 约 `#8c2828` |
| 字体栈（display） | `"STKaiti", "KaiTi", "隶书", "LiSu", serif` |
| 字体栈（body） | `"STKaiti", "KaiTi", "楷体", serif` |
| 装饰元素 | 竖排布局、简牍纹理（CSS repeating-linear-gradient）、麻绳编联感 |

## 3. 通用资产（无论选哪种风格均适用）

### LOGO 设计

- **方案 A（水墨）**：圆形朱砂印 + 篆书"石"字阴文
- **方案 B（绢帛）**：双线方框 + 隶书"石湖"二字 + 描金卷草
- **方案 C（简牍）**：竖向竹简形 + "詩"字篆刻
- 选定风格后统一应用，作为页眉 LOGO 与 favicon

### 字体 fallback

所有页面统一加载：
```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700&family=Ma+Shan+Zheng&display=swap" rel="stylesheet">
```

### 反 AI slop 规则

- ❌ 紫渐变（indigo-violet-pink）
- ❌ emoji 当 icon
- ❌ 圆角卡片 + 左边 accent border
- ❌ SVG 画人脸
- ❌ Inter / Geist 做 display font
- ✅ 用 oklch 色彩 + 宋楷字体 + CSS Grid + `text-wrap: pretty`
- ✅ 朱砂印章 + 墨色浓淡 + 留白

## 4. 页面结构约定

所有诗的 HTML 页面统一结构：

```
<header>
  - LOGO
  - 网站名 "唐诗三百首"
  - 返回导航链接
</header>

<main>
  <article>
    <section class="poem-title">诗题 + 作者</section>
    <section class="poem-meta">体裁 / 写作年代</section>
    <section class="poem-text">诗原文（按风格竖排或横排）</section>
    <section class="poem-tijie">题解</section>
    <section class="poem-notes">注释（编号列表）</section>
    <section class="poem-appreciation">赏析（含出处脚注）</section>
    <section class="poem-famous">名句圈点</section>
    <section class="poem-sources">出处溯源</section>
  </article>
  
  <aside class="poet-card">
    诗人简介摘要 + 点击展开浮窗（完整生平）
  </aside>
</main>

<footer>
  - 翻页：上一首 / 下一首
  - 返回诗人卷
  - 版权与出处声明
</footer>
```

## 5. 导航结构

- `/index.html` 标题页（含 LOGO 入场动画）
- `/navigation.html` 导航页（按诗人分卷 / 按体裁分卷 / 按主题分卷）
- `/poets/index.html` 诗人总索引
- `/poets/{poet-id}.html` 诗人详情页（含其所有诗作列表）
- `/poems/{poem-id}.html` 单首诗页面
- `/about.html` 关于本站与参考书目

## 6. 诗人浮窗机制

诗人简介采用"摘要 + 浮窗"模式：
- 诗页面侧栏：显示诗人姓名 + 朝代 + 一句话简介（约 50 字）
- 点击"查看生平"按钮：弹出浮窗显示完整诗人简介（约 200-300 字）
- 浮窗内可进一步链接到诗人详情页

## 7. 待用户确认

- 选定主风格后，全站统一采用
- LOGO 方案随主风格确定
- 字体方案随主风格确定
