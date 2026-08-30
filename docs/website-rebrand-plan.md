# agent-hive 官网 Logo 换肤改版计划（flash 逐阶段提示词集，复制粘贴即用）

> 目标：在不改任何文案、不改任何锚点/链接、不动信息架构的前提下，把 `site/index.html` 的绿色主题整体替换为「新 logo（天蓝蜂巢 + 近白底）」风格；并把 PWA 图标资产从旧绿色换成新 logo。
> 方法论：从桌面 `skill/taste-skill` 的前端设计技能集（taste-skill / imagegen-frontend-web / soft-skill）中**挑选可复刻的点**，不照抄（复刻/弃用清单见 §2）。
> 用法：按 §0 的顺序，一次复制一个代码块完整发给 flash 模型；每阶段提示词均已内嵌品牌规范卡与本节契约，flash 无需跨会话记忆。

---

## 0. 使用说明（先读，勿发给模型）

1. **模型选择**：Stage 1（出图）需要支持图像生成的 flash 系模型（如 `gemini-2.5-flash-image`）；其余阶段任意 flash 系文本模型即可。所有提示词均为中文，可直接粘贴。
2. **素材准备**：logo 文件已入库 `assets/logo.webp`（800×800，即桌面 `logo.webp` 的副本）。Stage 0/1/11 需要把这张图作为附件一起发给模型。
3. **执行顺序**：
   - Stage 0（品牌基调复核，1 次对话）→ Stage 1（10 张分节参考图）→ Stage 2（全局基础层，先行）→ Stage 3~10（各节独立，**互不依赖，可并行/乱序**，但每节回传产物都先存到暂存文件 `site/_rebrand_scratch.md`）→ Stage 11（PWA 资产）→ Stage 12（整页组装 + 总验收）。
   - 只有 Stage 2 必须先做（它产出的 CSS 变量是后面所有节的地基）；Stage 12 是最后一棒。
4. **工作目录**：`C:\Users\10104\Desktop\code\agent-hive`。所有改动只发生在 `site/` 目录内的 `index.html`、`manifest.webmanifest`、`sw.js`、`icons/`，**不得改动仓库其余任何文件**。
5. **总红线（每阶段内重复强调）**：
   - 文案一个字不改（除 `<title>`/`<meta description>`/`theme-color` 这类元信息按提示词要求改）；
   - 锚点 id、导航标签、外链 URL、Release 版本号（v0.2.0）一个不改；
   - 保持零遥测：不引入任何外部字体/脚本/CSS 文件，字体只用系统栈；
   - 保持 PWA：Service Worker 注册代码保留，缓存清单按 Stage 11 更新；
   - 不引入构建工具：最终产物仍是纯静态 `index.html` 内联 `<style>` + 少量内联 `<script>`。
6. **每阶段回传后你亲自做的门禁**（§8 有完整清单）：双击打开 `site/index.html`，核对锚点能跳、徽章能显示、深色模式正常、窄屏正常、无外链资源请求（F12 网络面板应只有 shields.io 徽章）。
7. **回滚**：每完成一个 Stage 建议 `git commit` 一次（commit message 形如 `style(site): rebrand stage N - hero`），不满意单节可 `git checkout -- site/index.html` 回滚该节。

---

## 1. Logo 品牌基因卡（程序化分析结论，设计事实锁定）

对 `assets/logo.webp`（800×800）的像素级分析结果：

| 维度 | 事实 | 设计含义 |
|---|---|---|
| 画布 | 800×800 正方形 | 主视觉比例 1:1，任何地方引用建议等比缩放（160/120/96/48px 档） |
| 底色 | `#F7F8F8` 近白（占 94.4%），冷调、无纹理 | 全局页面底色直接用此值，品牌即背景 |
| 主色 | `#82B9DE` / `#7DB9E0` 天空蓝（主体渐变带） | 品牌主色；饱和度约 55%，符合 taste-skill「饱和度 < 80%」纪律 |
| 辅助色 | `#A9CBE1`（浅）、`#7AABCC`/`#7AB6DA`（深一点的天蓝） | 蓝色阶四级：浅→主→深→墨，用作设计系统 ramp |
| 图形 | 中央大型「六边形蜂巢」（由六边形格拼成，占位约 x236-563/y242-561，即画面中央 41%），底部两个小六边形格（约 x240-400/y470-560） | **六边形 = 唯一视觉母题**。任何装饰元素只允许：六边形、蜂巢格、蜜蜂、圆点；禁止圆形 blob、禁止曲线流线 |
| 文字 | 无 | logo 为纯图形标，页面品牌字标用系统字体自排 |
| 深色像素 | 无（无纯黑、无深色描边） | 风格=轻盈、柔和、留白；**禁用纯黑 `#000`**，正文用冷调近黑 |
| 风格气质 | 极简、扁平、浅色、几何、干净 | 对应 taste-skill 组合引擎：Pristine Light Mode（浅色纯净）+ Soft Structuralism（柔和投影、大量留白） |

一句话品牌定位（Design Read，供所有 flash 提示词统一口径）：

> **「阅读为：面向技术开发者的开源工具官网，用轻盈柔和的浅色几何语言（天蓝蜂巢），传达『契约 = 结构、蜂群 = 协作』的信任感与秩序感。」**

---

## 2. taste-skill 复刻 / 弃用清单（挑选，不照抄）

### 2.1 复刻（本计划实际采用）

| 来源 | 复刻点 | 落地位置 |
|---|---|---|
| taste-skill §0 | **Brief Inference**：先给出一句话 Design Read，所有决策从它推导 | §1 末句；每个 flash 提示词开头重申 |
| taste-skill §1 | **三旋钮**：DESIGN_VARIANCE=5 / MOTION_INTENSITY=3 / VISUAL_DENSITY=3（按「极简/柔和」映射） | 贯穿 §3 全部动效与密度决策 |
| taste-skill §4.2 | **调色板纪律**：1 主色 + 1 辅助 + 1 点缀 + 中性阶；全站色彩一致性锁定；无霓虹辉光 | §3.1 色彩 ramp |
| taste-skill §11 | **Redesign Protocol**：先审计（品牌 token/IA/内容块/保留与退休清单/SEO 基线），锚点与文案、导航标签、URL 一律不动；现代化杠杆按「排版→间距→色彩→动效→Hero 重排」顺序施力 | §4 审计清单、各 Stage 保留约束 |
| imagegen-frontend-web §2 | **组合变化引擎**：主题范式、背景性格、字体性格、Hero 结构、签名组件（4 个）、动效语言（2 个）、叙事主线、Second-Read Moment 全部预先掷定，flash 只负责执行不负责发明 | §5 蓝图决策表 |
| imagegen-frontend-web §6/§16 | **每节一张参考图 + 多图一致性规则**（同一品牌世界：同色板、同排版逻辑、同图标气质；允许变的是构图锚点与背景模式） | Stage 1 出图契约 |
| imagegen-frontend-web §8 | **Anti-AI-Slop 黑名单**（针对本项目筛选）：无无限居中、无三张等宽卡、无紫色渐变、无玻璃拟态堆叠、无假产品截图、无渐变文字 | §4.2 退休清单、Stage 12 验收 |
| imagegen-frontend-web §13 | **渐变纪律**：允许低饱和同色系色调渐变（天蓝→更浅天蓝），禁止彩虹/网格 blob 渐变 | Hero 与代码面板背景 |
| soft-skill | **Soft Structuralism 气质**：近白背景、大字号粗体标题、弥散柔和蓝色调投影、`py-24` 级宏白、IntersectionObserver 渐入、只用 transform/opacity 动效、禁用 `h-screen` 改用 `min-h-[100dvh]` | §3.5 动效规范 |
| taste-skill §6 | **无障碍护栏**：焦点环、对比度 ≥4.5:1、`prefers-reduced-motion` 全关动效 | §3.6、§8 验收 |

### 2.2 弃用 / 适配（含理由，防止 flash 误抄）

| taste-skill 原文 | 本项目决定 | 理由 |
|---|---|---|
| 禁用 Inter 等默认字体 | 采用系统字体栈（见 §3.2） | 本站「零遥测」承诺禁止外链 Google Fonts；taste-skill 的精神是「不要默认感」，我们按同一精神对系统栈做了品牌化排序 |
| em-dash 全面禁令 | 仅对英文/装饰性破折号生效；中文正文保留规范标点「——」 | 原禁令面向英文营销页的视觉 Tell；中文文档/站点用「——」是标准排版，去除装饰性滥用即可 |
| 按钮套按钮、磁吸悬浮等 agency 炫技 | 弃用 | 与「轻盈、可信、开源工具」定位不符（MOTION_INTENSITY=3） |
| bento 大改版构图 | 仅下载区采用 2×2 不对称卡片格 | 表格/代码面板的信息密度是本项目可信度来源，整体保留 |
| 数字编号 eyebrow（01/02/03） | 全站移除，改用主题词 eyebrow | 现行站点的「01 下载…」正是 AI-tells 黑名单条目；但注意：**这是唯一允许改动文案的例外**（删编号数字本身，节标题文字保留） |
| 默认 emoji 策略（禁 emoji） | 保留 🐝/🪟/🍎/🐧/🐍 等既有语义 emoji | 现有站点信息密集，emoji 承担平台图标职责；仅新增六边形 SVG 装饰，不新增无关 emoji |
| serif 禁用 | 沿用（本项目用系统无衬线栈） | 无需变动 |
| 全站禁 3 张等宽卡 | 差异化四维表从「表格」改为「2×2 六边形角标卡片」（非 3 张等宽） | 保留信息密度同时消除 Tell |

---

## 3. 设计系统规范卡（Design Tokens，精确到值）

> 这是全计划的**单一事实源**。所有 flash 阶段提示词会内嵌此卡的紧凑版；本节是全量版，供你核对与后续手工微调。

### 3.1 色彩（浅色）

```css
:root {
  color-scheme: light dark;
  /* 中性阶（冷调，与 logo 底色同族） */
  --bg: #F7F8F8;            /* 页面底 = logo 底色，全站唯一底色 */
  --surface: #FFFFFF;       /* 卡片/代码面板抬升面 */
  --surface-2: #F1F6FA;     /* 次级填充（表头、hover 底） */
  --ink: #1C2B38;           /* 正文：冷调近黑，禁纯黑 #000 */
  --muted: #5B7185;         /* 次级文字，白底对比度 4.7:1 */
  --hairline: #DCE7EF;      /* 分隔线/边框：带蓝的冷灰 */
  /* 品牌蓝 ramp（由 logo 色值推导） */
  --hive-50: #F4F9FC;
  --hive-100: #E6F1F9;
  --hive-200: #CFE4F2;
  --hive-300: #A9D1E8;      /* logo 浅调（#A9CBE1 归整） */
  --hive-400: #82B9DE;      /* logo 主色 */
  --hive-500: #5FA6D6;      /* 交互/描边 */
  --hive-600: #3D87BD;
  --hive-700: #2F6FA0;      /* 链接/按钮底：白底文本 5.2:1 */
  --hive-800: #245A85;      /* 深底反白 7.5:1 */
  --hive-900: #1B4465;      /* Hero/页脚深色带 */
  /* 点缀色：蜂王浆琥珀，全站至多出现 2 处（品牌字标蜂点 + 徽章行），绝不承载正文 */
  --honey: #EBA22C;
  /* 代码面板（浅色下用「浅色代码面」保持轻盈，不是暗黑块） */
  --code-bg: #F2F7FB;
  --code-border: #DCE7EF;
  --code-ink: #1C2B38;
  --code-muted: #6B8599;    /* 注释 */
  --code-key: #2F6FA0;      /* 关键字/命令 */
  /* 阴影：弥散、低饱和、带品牌蓝调 */
  --shadow-sm: 0 1px 2px rgba(27,68,101,.06);
  --shadow-md: 0 8px 24px -12px rgba(27,68,101,.18);
  --shadow-lg: 0 16px 40px -16px rgba(27,68,101,.25);
  --focus-ring: 0 0 0 3px rgba(95,166,214,.45);
  /* 徽章 */
  --note-bg: #F4F9FC;  --note-border: #82B9DE;  --note-fg: #245A85;
  /* 旧绿色变量全部删除：--green-* 系列一律不再出现 */
}
```

### 3.2 色彩（深色，`prefers-color-scheme: dark`）

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0F1B26;          /* 深海军蓝，蜂巢之夜 */
    --surface: #152433;
    --surface-2: #1A2C3D;
    --ink: #E8F0F6;
    --muted: #93A8BB;       /* 深底 6.1:1 */
    --hairline: #23384B;
    --hive-100: #1A2C3D;    /* 深色下「浅蓝」重映射为深面板 */
    --hive-300: #7FB8DE;    /* 深底文字级强调色（8.0:1） */
    --hive-400: #82B9DE;
    --hive-500: #5FA6D6;
    --hive-600: #6FAED9;
    --hive-700: #8CC3E6;    /* 深底链接色 */
    --hive-900: #0A1420;    /* 深色下最深带 */
    --honey: #F5B94C;
    --code-bg: #0B1620;  --code-border: #1E3244;
    --code-ink: #DCE9F3; --code-muted: #7A93A8; --code-key: #7FB8DE;
    --note-bg: #14283A; --note-border: #2F6FA0; --note-fg: #A9D1E8;
  }
}
```

### 3.3 字体（系统栈，零外链）

```css
/* 正文：西文用系统 UI 字族，中文落到 PingFang/鸿蒙/小米兰亭 */
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui,
             "PingFang SC", "HarmonyOS Sans SC", "MiSans",
             "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
/* 代码：等宽系统栈 */
font-family: ui-monospace, "SF Mono", "Cascadia Code", "JetBrains Mono",
             Consolas, "Liberation Mono", monospace;
```

- 标题权重 700-800，`letter-spacing: -0.01em`（西文收紧，中文自动无感）；
- 正文 1rem / 行高 1.75，段落最大宽度 `max-width: 65ch`；
- 字号阶：h1 `clamp(2rem, 5vw, 2.6rem)` / h2 `1.45rem` / h3 `1.1rem` / 小字 `.875rem`；
- **不引入任何 webfont**（零遥测红线）。

### 3.4 形状语言（六边形母题使用规则）

- **圆角**：卡片/面板 10px；按钮 8px；代码面板 10px；徽章 999px。禁止大圆角（20px+）胶囊化一切。
- **六边形只出现在 4 个指定位置**（超过即滥用）：
  1. Hero 顶部 logo 图（`assets/logo.webp`，120px）；
  2. Hero 背景：六边形点阵纹理（低透明度 SVG data-uri，见 Stage 2 提示词）；
  3. 各节 h2 前的 18px 六边形小图标（内联 SVG，蜂巢格线）；
  4. 架构图 SVG 的节点形状（矩形 → 尖顶六边形，见 Stage 8）。
- **六边形列表项目符号**（仅安全/特性列表用）：10px 元素，
  `clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%); background: var(--hive-400);`
- **禁**：六边形裁切照片/卡片（clip-path 放卡片上会切字、破坏对比度与可读性）。

### 3.5 动效规范（MOTION_INTENSITY = 3）

```css
:root { --ease-out: cubic-bezier(0.25, 1, 0.5, 1);   /* 入场 */
        --ease-hover: cubic-bezier(0.32, 0.72, 0, 1); /* 悬停（Apple 曲线） */ }
```

- **入场**：`.reveal { opacity:0; transform: translateY(12px); transition: opacity .26s var(--ease-out), transform .26s var(--ease-out); }`，`.reveal.in { opacity:1; transform:none; }`；由 IntersectionObserver（threshold 0.15，触发一次即断开）加 `.in`；同级元素 stagger `transition-delay: 45ms × i`（最多延迟 4 个）；
- **悬停**：按钮 `translateY(-1px)` + `--shadow-md`；链接下划线 2px `--hive-400`；卡片 hover 边框变 `--hive-400`（不位移、不放缩）；
- **导航**：保持 sticky + 毛玻璃（`backdrop-filter` 仅用于 nav 这个 fixed/sticky 元素），滚过 8px 后加 `--shadow-sm`；
- **禁**：视差、滚动劫持、无限循环动画、粒子、光标跟随、`top/left/width/height` 动画（只用 transform/opacity）；
- **`prefers-reduced-motion: reduce`**：关闭全部 transform/transition，`.reveal` 直接可见；
- 全高区块用 `min-height: 100dvh`（等价物），禁止 `height: 100vh`。

### 3.6 无障碍护栏（保留现行优势，不得回退）

- 焦点可见：`:focus-visible { outline: 2px solid var(--hive-500); outline-offset: 2px; }`；
- 正文/次级文字对比度 ≥ 4.5:1（§3.1 各值已达标，改色时查表）；
- 所有装饰 SVG `aria-hidden="true"`，架构图保留 `role="img"` 与 `aria-label`；
- 手风琴 `summary` 保留键盘可达；链接 `rel="noopener"` 不变。

---

## 4. 现状审计（保留 / 退休清单）

### 4.1 保留（任何阶段不得改动）

| 项 | 明细 |
|---|---|
| 信息架构 | 全部锚点：`#top #download #demo #differentiators #benchmark #architecture #quickstart #security #faq`；导航 8 个标签文字与顺序 |
| 文案 | 除「删除 01-08 编号数字」与 `theme-color`/`title` 内主题描述外，正文一个字不改 |
| 链接 | 全部 GitHub 直链、Releases 版本 v0.2.0、仓库地址 |
| 表格数据 | 差异化四维表、Benchmark 全部数字（1.0000/0.0000/129/129、$0.0040 等）逐字保留 |
| 架构图 | SVG 内容（首脑 + 4 专家 + 连线语义 + `aria-label`），只改形状与颜色 |
| PWA | `manifest.webmanifest` 引用、Service Worker 注册逻辑、iOS 安装说明 |
| 零遥测 | 无统计脚本、无外链字体；唯一外链 = shields.io 徽章 |

### 4.2 退休（本计划的改动面，除此之外不动）

| 项 | 处置 |
|---|---|
| 绿色主题 `--green-*` 全系（#14532d 系） | 删除，替换为 §3 蓝色 ramp |
| Hero 深绿渐变横幅 | 改为近白底 + 六边形点阵纹理 + 天蓝 logo 居中构图（见 Stage 3） |
| `h2` 的「01/02/…」编号 eyebrow | 删除数字，改为 18px 六边形 SVG 图标；h2 文本保留 |
| 等宽三/四列卡片平铺 | 下载区改 2×2 不对称格（见 Stage 4）；差异化四维表改 2×2 卡片（见 Stage 6） |
| 绿色 favicon/图标（#0F482D 系） | 由新 logo 重新生成全尺寸图标（Stage 11） |
| `theme-color` `#14532d` | 浅色 `#7DB9E0` / 深色 `#0F1B26` 双 meta（Stage 11） |

---

## 5. 目标站点蓝图（组合引擎已预先掷定，flash 只执行）

三旋钮：DESIGN_VARIANCE=5 · MOTION_INTENSITY=3 · VISUAL_DENSITY=3
主题范式：Pristine Light Mode（浅色纯净）｜背景性格：纯色 + 六边形点阵纹理｜字体性格：系统无衬线强层级
Hero 结构：Stacked Center 居中堆叠（明确**不用**左文右图）｜叙事主线：Living System（蜂巢生长：首脑=蜂王，专家=工蜂）
签名组件（恰好 4 个）：① 六边形列表符 ② 下载区 2×2 bento ③ 架构图六边形节点 ④ 蜂巢格 h2 图标
动效语言（恰好 2 个）：① staggered float-up 渐入 ② 手风琴平滑展开
Second-Read Moment（全站仅 1 处）：品牌字标「蜂群」旁的琥珀色小六边形点（`--honey`）

| 节（锚点） | 任务（Job） | 构图锚点 | 背景模式 | 参考图产出 |
|---|---|---|---|---|
| Hero `#top` | 3 秒建立品牌与定位 | 居中堆叠：logo→h1→lead→徽章→按钮 | 近白底 + 六边形点阵 + 极淡径向天蓝 | 图 1 |
| 下载 `#download` | 转化：拿到安装包 | 2×2 bento（四卡两两错落，徽章式平台图标） | 纯白卡片浮于底色 | 图 2 |
| 演示 `#demo` | 证明「一条命令可用」 | 左右双栏代码面板（桌面）/ 单栏（窄屏） | 浅色代码面 | 图 3 |
| 差异化 `#differentiators` | 立住四个卖点 | 2×2 蜂巢角标卡片（非 3 等宽） | 卡片 + 六边形角标 | 图 4 |
| 基准 `#benchmark` | 可信度：真实数字 | 横向指标条（数字大字号 + 单位小字） | 指标条 + 注释块 | 图 5 |
| 架构 `#architecture` | 一图看懂协作 | 居中 SVG，节点=尖顶六边形 | 六边形节点 + 浅色画布 | 图 6 |
| 快速开始 `#quickstart` | 降低上手成本 | 单栏代码面板 + 右侧说明条 | 浅色代码面 | 图 7 |
| 安全 `#security` | 信任：透明声明 | 六边形符列表（左） | 列表 + 轻量边框卡片 | 图 8 |
| FAQ `#faq` | 消除顾虑 | 手风琴，展开态天蓝描边 | 卡片行 | 图 9 |
| 页脚 | 收尾 + 零遥测声明 | 深海军蓝带（--hive-900 渐变） | 深色带 + 反白字 | 图 10（与图 9 拼在同一画布下半部即可） |

---

## 6. 阶段总览

| Stage | 名称 | 依赖 | 产出 |
|---|---|---|---|
| 0 | 品牌基调复核（可选但推荐） | 无 | 品牌分析一句话确认（附 logo 图） |
| 1 | 10 张分节参考图 | 无（建议先做 Stage 0） | 10 张 16:9 设计参考图 |
| 2 | 全局基础层（CSS 变量/字体/nav/footer/纹理/入场机制） | 无 | `<style>` 基础段 + nav/footer HTML |
| 3 | Hero | Stage 2 | Hero HTML + CSS |
| 4 | 下载区 | Stage 2 | 下载区 HTML + CSS |
| 5 | 演示区 | Stage 2 | 演示区 HTML + CSS |
| 6 | 差异化四维 | Stage 2 | 四维卡片 HTML + CSS |
| 7 | Benchmark | Stage 2 | 指标条 HTML + CSS |
| 8 | 架构图 | Stage 2 | 六边形节点 SVG + CSS |
| 9 | 快速开始 + 安全 | Stage 2 | 两节 HTML + CSS |
| 10 | FAQ + 页脚深色带 | Stage 2 | FAQ/页脚 HTML + CSS |
| 11 | PWA 资产（图标/manifest/sw.js/theme-color） | 无 | 新图标文件 + 3 处元信息 |
| 12 | 整页组装 + 总验收 | 2-11 全部 | 最终完整 `site/index.html` |

---

## 7. 逐阶段完整提示词

### 7.0 Stage 0：品牌基调复核

```text
你是字节跳动前端的资深设计系统专家。请复核一份品牌分析，并给出最终设计基调。

【背景】开源项目 agent-hive（蜂群：契约驱动的多智能体编排框架）刚完成新 logo，
准备把官网（纯静态 HTML + 内联 CSS，GitHub Pages，零遥测）从旧绿色主题整体换肤为新 logo 风格。
我已对 logo 做了程序化像素分析，请你对照附件的 logo.webp 逐条复核，纠正任何错误或遗漏。

【我的分析】
1. 画布 800×800，底色近白 #F7F8F8（占约 94%），冷调。
2. 主体：中央大型六边形蜂巢（由六边形格组成），主色 #82B9DE / #7DB9E0 天空蓝，
   辅助浅色 #A9CBE1、深色 #7AABCC；无深色描边、无文字、无纯黑。
3. 底部有两个小六边形格（约 x240-400 / y470-560）。
4. 风格：极简、扁平、浅色、几何、轻盈。

【请复核并输出】
1. 上述 4 条逐条判定「正确 / 需修正」，需修正的给出修正值（色值精确到 hex）。
2. 一句话 Design Read（格式：阅读为……面向……用……语言，传达……）。
3. 三旋钮建议值：DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY（各 1-10，说明理由，各不超过一句话）。
4. 这个 logo 若出现在「浅色科技官网」上，最忌讳的 3 种风格误用（例如：往深色赛博方向做）。

【回传格式】四段，每段不超过 8 行，中文。
```

### 7.1 Stage 1：10 张分节参考图（需支持出图的 flash 模型）

```text
你是顶级前端视觉设计师（art director）。为一个开源技术项目官网生成「分节设计参考图」，
供前端工程师 1:1 还原成 HTML/CSS。每张图只表达一个页面分节，共 10 张，逐张输出。

【品牌规范卡（全 10 张必须严格遵守，违者视为失败）】
- 主题：浅色纯净风。页面底色 #F7F8F8，卡片纯白 #FFFFFF，分隔线 #DCE7EF。
- 色彩：主色天空蓝 #82B9DE，深阶 #2F6FA0 / #245A85，墨色文字 #1C2B38（禁纯黑），
  次级文字 #5B7185；点缀琥珀 #EBA22C 只允许出现在「品牌字标旁的蜂点」这一处。
- 图形母题：六边形/蜂巢格/蜜蜂。禁止圆形 blob、曲线流线、玻璃拟态、霓虹辉光、紫蓝渐变。
- 字体：现代无衬线（参考 Geist / Segoe UI 气质），中文可用思源黑体气质；标题粗体大字号，正文 16px 级。
- 质感：柔和弥散投影（阴影带淡蓝调），大量留白，卡片圆角约 10px（禁止胶囊大圆角）。
- 严禁：三张等宽卡并排、左文右图 Hero、渐变文字、假产品截图、装饰性英文标语。
- 一致性：10 张之间同一品牌世界——同色板、同排版逻辑、同图标线宽；允许变化的是构图锚点与背景模式。

【10 张分节图逐张契约】
图1 Hero：居中堆叠。顶部小 logo（天蓝蜂巢，约 120px）→ 大标题「agent-hive 蜂群」→
  一行副标题 → 一排徽章 → 一个天蓝圆角按钮。背景近白，满布极淡的六边形点阵纹理
  （#82B9DE 透明度约 15%），标题下方有一枚琥珀色小六边形点（全站唯一的琥珀）。
图2 下载区：2×2 不对称卡片格（四张卡片，两列不等高、错落），每卡一个平台图标 +
  平台名 + 下载按钮 + 一句小字说明；卡片纯白、投影柔和。
图3 演示：左右双栏两块「浅色代码面板」（#F2F7FB 底 + 等宽深蓝文字 + 顶栏三个小点），
  左边命令行、右边 Python 代码；面板标题小字标注组件名。
图4 差异化四维：2×2 四张卡片，每卡左上角一个六边形角标（内嵌编号 ①-④），
  卡内加粗标题 + 两行说明 + 底部证据路径小字；蓝色阶依次深浅。
图5 Benchmark：横向指标条，大号数字（如 1.0000）+ 小字单位/说明，两条数据行，
  底部一块浅蓝注释条（#F4F9FC 底 + #82B9DE 左边线）。
图6 架构图：中央一个较大六边形节点（首脑 Chief，天蓝填充白字），四周四个小六边形节点
  （编码/测试/评审/调研，浅蓝填充深蓝描边），细线箭头从中央指向四周；画布近白，带淡蜂巢纹理。
图7 快速开始：单栏宽代码面板（3 行带 # 注释的命令）+ 右侧细窄说明条；浅色代码面。
图8 安全与隐私：五条列表，每条左侧一个 10px 天蓝六边形项目符，文字深蓝灰；外围一圈极浅边框卡片。
图9 FAQ：手风琴列表，五条折叠项；展开的那条顶部天蓝描边加粗、其余浅灰分隔线；每项标题前一个小六边形。
图10 页脚：深海军蓝带（#1B4465→#245A85 渐变），左对齐白色版权行与零遥测声明，右上角一枚浅蓝蜂巢小图。

【输出要求】
- 每张图横向 16:9，风格统一；逐张输出并在图前标注「Section N/10：名称」。
- 图内出现的文字用真实内容（中文）：标题、按钮文字、命令等按上面契约写，禁止 Lorem Ipsum。
- 不要在一张图里塞两节内容。
```

### 7.2 Stage 2：全局基础层

```text
你是字节跳动前端的资深工程师，负责一个纯静态官网（单文件 HTML + 内联 CSS，无构建工具）
的品牌换肤工程。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只做「全局基础层」：CSS 变量、字体栈、顶部导航、页脚、入场动效机制、Hero 背景纹理。
只改 site/index.html 里的 <style> 基础段与 nav/footer 两个区块，其余节一律不动。

【品牌规范卡（本工程全阶段锁定）】
- 浅色：--bg:#F7F8F8; --surface:#FFFFFF; --surface-2:#F1F6FA; --ink:#1C2B38; --muted:#5B7185;
  --hairline:#DCE7EF; --hive-50:#F4F9FC; --hive-100:#E6F1F9; --hive-200:#CFE4F2;
  --hive-300:#A9D1E8; --hive-400:#82B9DE; --hive-500:#5FA6D6; --hive-600:#3D87BD;
  --hive-700:#2F6FA0; --hive-800:#245A85; --hive-900:#1B4465; --honey:#EBA22C;
  --code-bg:#F2F7FB; --code-border:#DCE7EF; --code-ink:#1C2B38; --code-muted:#6B8599;
  --code-key:#2F6FA0; --shadow-sm:0 1px 2px rgba(27,68,101,.06);
  --shadow-md:0 8px 24px -12px rgba(27,68,101,.18); --shadow-lg:0 16px 40px -16px rgba(27,68,101,.25);
  --focus-ring:0 0 0 3px rgba(95,166,214,.45); --note-bg:#F4F9FC; --note-border:#82B9DE; --note-fg:#245A85;
- 深色（prefers-color-scheme: dark）：--bg:#0F1B26; --surface:#152433; --surface-2:#1A2C3D;
  --ink:#E8F0F6; --muted:#93A8BB; --hairline:#23384B; --hive-100:#1A2C3D; --hive-300:#7FB8DE;
  --hive-400:#82B9DE; --hive-500:#5FA6D6; --hive-600:#6FAED9; --hive-700:#8CC3E6; --hive-900:#0A1420;
  --honey:#F5B94C; --code-bg:#0B1620; --code-border:#1E3244; --code-ink:#DCE9F3; --code-muted:#7A93A8;
  --code-key:#7FB8DE; --note-bg:#14283A; --note-border:#2F6FA0; --note-fg:#A9D1E8;
- 字体（零外链，系统栈）：正文 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui,
  "PingFang SC", "HarmonyOS Sans SC", "MiSans", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif；
  代码 ui-monospace, "SF Mono", "Cascadia Code", "JetBrains Mono", Consolas, "Liberation Mono", monospace。
- 形状：卡片/面板圆角 10px；按钮 8px；徽章 999px。禁大圆角胶囊化。
- 动效：--ease-out:cubic-bezier(0.25,1,0.5,1)；--ease-hover:cubic-bezier(0.32,0.72,0,1)。
  只用 transform/opacity；prefers-reduced-motion 时全部关闭。
- 红线：禁纯黑 #000；禁霓虹辉光；禁外链资源；全高区块用 min-height:100dvh。

【本阶段契约】
1. :root 与深色媒体查询：按上述卡完整落成 CSS 变量；删除旧 --green-* 全部变量及引用。
2. body：背景 var(--bg)、文字 var(--ink)、1rem/1.75 行高；a 色 var(--hive-700)（深色 var(--hive-700) 已重映射为 #8CC3E6）。
3. 顶部导航 nav.top：
   - 保持 sticky + 毛玻璃（backdrop-filter 只允许用在此处），滚动超过 8px 时加 var(--shadow-sm)（IntersectionObserver 或滚动监听均可，需被动）；
   - 品牌字标「🐝 agent-hive 蜂群」改为：蜂点用一枚 12px 琥珀六边形（--honey，clip-path 六边形）替换 🐝 表情符号位置，
     其余文字保持原文案，颜色 var(--hive-700)，字重 700；
   - 链接 hover 下划线 2px var(--hive-400)。
4. 页脚 footer：深色带，background: linear-gradient(135deg, var(--hive-900), var(--hive-800))；
   内部文字全部反白（#fff，次级 rgba(255,255,255,.78)）；链接色 #A9D1E8；版权与零遥测两行文案原样保留。
5. 入场动效机制：定义 .reveal/.reveal.in 类（opacity 0→1，translateY(12px)→0，0.26s var(--ease-out)；
   同级 stagger 用 transition-delay:45ms*序号，最多 4 级）；页脚 <script> 里写 IntersectionObserver
   （threshold 0.15，触发一次后 unobserve）；reduced-motion 时 .reveal 直接可见。
6. Hero 背景纹理（供下一阶段使用，本阶段先定义类）：.hex-field 背景图 =
   data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='78' viewBox='0 0 120 78'%3E%3Cg fill='none' stroke='%2382B9DE' stroke-opacity='0.15'%3E%3Cpath d='M30 8l13 7.5v15l-13 7.5-13-7.5v-15z'/%3E%3Cpath d='M90 8l13 7.5v15l-13 7.5-13-7.5v-15z'/%3E%3Cpath d='M60 38l13 7.5v15l-13 7.5-13-7.5v-15z'/%3E%3C/g%3E%3C/svg%3E
   （重复平铺，不随滚动视差）。
7. :focus-visible：outline 2px var(--hive-500)，offset 2px。
8. 删除 h2 的「.no 编号」样式（编号数字将在各节移除）。

【保留约束】不改任何正文文案、锚点、链接；不改 <main> 内各 section 的结构与内容；
Service Worker 注册脚本原样保留。

【回传格式】① 完整的 <style> 基础段代码；② 新的 nav 与 footer HTML；③ 入场动效 <script> 代码；
④ 改动点清单（每处一行：文件内位置 + 改了什么）。不要求你运行构建（无构建），
但需自查：CSS 变量名与规范卡一致、无 --green-* 残留、无外链资源。
```

### 7.3 Stage 3：Hero

```text
你是字节跳动前端的资深工程师。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只改造 site/index.html 的 <header class="hero"> 区块（锚点 #top 必须保留）。
基础层（CSS 变量/纹理 .hex-field/.reveal 机制）已由前序阶段完成，直接引用。

【品牌规范卡】
- 浅色主题：底色 var(--bg)=#F7F8F8；主色 --hive-400=#82B9DE；深阶 --hive-700=#2F6FA0；
  墨色 var(--ink)=#1C2B38（禁纯黑）；点缀 --honey=#EBA22C 全站仅允许出现在品牌字标蜂点，
  Hero 内不得出现琥珀。
- 构图：居中堆叠（Stacked Center），明确禁止左文右图。
- 动效：入场用 .reveal 机制（logo/h1/lead/徽章/按钮依次 stagger 45ms）；hover 按钮 translateY(-1px)+var(--shadow-md)。

【本阶段契约】
0. 前置一步（你本地执行，非 flash 任务）：把仓库根的 assets/logo.webp 复制为
   site/logo.webp（PowerShell：Copy-Item assets\logo.webp site\logo.webp）。
   原因：GitHub Pages 只发布 site/ 目录，引用 ../assets/logo.webp 在线上会 404。
1. 结构顺序：<img class="hero-logo" src="./logo.webp" alt="agent-hive 蜂群 logo">（宽 120px，
   等比；HTML 在 site/ 目录内，相对路径 ./logo.webp）→ <h1>agent-hive 蜂群</h1>
   （字号 clamp(2rem,5vw,2.6rem)，字重 800，letter-spacing -0.01em，颜色 var(--ink)）
   → <p class="lead">（原 lead 文案原样保留，颜色 var(--muted)，max-width 46em）
   → 徽章行（原 4 个 shields.io 徽章链接与 alt 原样保留，居中）
   → <a class="btn-hero">GitHub 仓库 ↗</a>（背景 var(--hive-700)，白字，圆角 8px，hover 背景 var(--hive-600)）。
2. 背景：header.hero 由「深绿渐变」改为：background: var(--bg) + 叠加 .hex-field 纹理类
   + 顶部一圈极淡径向天蓝光 background-image:
   radial-gradient(ellipse 80% 60% at 50% 0%, rgba(130,185,222,.16), rgba(130,185,222,0) 70%)；
   两背景图同时叠加时 hex-field 在上、径向光在下。
3. 区块 padding：上下 4.5rem/3.5rem（桌面/移动），min-height: min(100dvh, 720px) 且内容垂直居中
   （flex column + justify-content:center）；给足留白。
4. h1 与 logo 之间间距 1.25rem；lead 与徽章行之间 1rem。
5. 全部新增元素挂 .reveal（logo 第一个，之后依次加 45ms 延迟，最多 4 级）。

【保留约束】lead 文案、4 个徽章 URL 与 alt、按钮文字与链接、锚点 id="top" 原样保留；
不改 <nav> 与 <main>。

【回传格式】① 新的 <header class="hero"> 完整 HTML；② 本区块新增 CSS（含响应式）；
③ 改动点清单。自查：无 --green-* 残留、无纯黑、无外链字体、徽章链接未变。
```

### 7.4 Stage 4：下载区

```text
你是字节跳动前端的资深工程师。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只改造 site/index.html 的 <section id="download"> 区块，锚点 id 必须保留。

【品牌规范卡】
- 卡片纯白 var(--surface)，圆角 10px，边框 1px var(--hairline)，hover 时边框变 var(--hive-400)；
  投影 var(--shadow-sm)，hover 抬升为 var(--shadow-md)（translateY(-1px)）。
- 按钮主样式：背景 var(--hive-700)，白字，圆角 8px，hover var(--hive-600)；ghost 样式：
  透明底 + 1.5px 边框 var(--hive-400) + 文字 var(--hive-700)，hover 填充 var(--hive-100)。
- 平台图标保留现有 emoji（🪟🍎🐧🐍），字号 1.7rem。
- 蓝色阶只用于强调元素，整卡禁止大面积天蓝填充（保持轻盈）。

【本阶段契约】
1. 布局：.dl-grid 改为不对称 2×2 bento：grid-template-columns: 1.2fr 1fr（桌面）；
   第一张 Windows 卡横跨两列（grid-column: 1 / -1），内容左文右按钮（这是本页唯一允许的
   「左文右元素」位置，且是卡片内部非图文 Hero）；macOS/Linux/Python 三卡在其下自然成行
   （第 3 张卡在窄屏时横跨两列）。
   窄屏（<=768px）全部单列。
2. 卡片内部顺序保持：平台图标 → 平台名 h3 → 主下载按钮 → 附按钮/命令代码块 → .dl-note 小字。
   所有链接、文件名、v0.2.0 版本号、pip 命令文案原样保留。
3. .dl-card pre 代码块：使用浅色代码面（背景 var(--code-bg)，边框 var(--code-border)，
   文字 var(--code-ink)，注释 var(--code-muted)）。
4. h2 标题：删除「01」编号 span，改为 18px 六边形 SVG 图标（尖顶六边形，描边 var(--hive-500)，
   内部再画一格小六边形，aria-hidden="true"），图标与文字间距 .5rem；下边框改 2px solid var(--hive-400)。
5. iOS 说明条 .ios-note：虚线边框改 var(--hive-400)，背景 var(--hive-50)，文案原样。
6. 各卡片挂 .reveal，stagger 45ms。
7. 本区块所有 h2 均按第 4 条的「六边形图标 + 天蓝下边框」样式处理（后续各节同规则）。

【保留约束】四个下载链接 URL、macOS 指向 Release 页、pip 命令、.dl-note 文案、
「iOS PWA 安装」说明文案、Release 主页链接全部原样。

【回传格式】① 新的下载区完整 HTML；② 本区块新增/修改 CSS；③ 改动点清单。
自查：无 --green-* 残留、无三张等宽卡并排、bento 在 768px 以下正确折叠。
```

### 7.5 Stage 5：演示区

```text
你是字节跳动前端的资深工程师。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只改造 site/index.html 的 <section id="demo"> 区块，锚点 id 必须保留。

【品牌规范卡】
- 浅色代码面：背景 var(--code-bg)=#F2F7FB，边框 1px var(--code-border)，圆角 10px；
  文字 var(--code-ink)，注释 var(--code-muted)，命令/关键字 var(--code-key)；
  面板顶部加一条「终端栏」：3 个小圆点（#A9D1E8 系浅蓝，非红黄绿）+
  右侧文件名小字（var(--code-muted)），高 28px。
- 深色模式自动切换为深色代码面（变量已在前序阶段定义）。
- 禁止：纯黑代码底、霓虹语法高亮（代码面板只允许 墨/灰/天蓝 三色）。

【本阶段契约】
1. 布局：桌面端两个演示块左右双栏（grid-template-columns: 1fr 1fr，间距 1.25rem），
   每块 = 小标题 h3 + 代码面板；<=900px 时单栏堆叠。
2. 代码面板：把现有 <pre><code> 包进 .code-panel（面板头 + pre），
   ① 面板标题分别写「hive-security · CLI」与「hive-cost · Python」；
   ② 代码内容逐字原样保留（含中文注释与退出码说明）；
   ③ 注释行给 .code-muted 类、命令名与关键字给 .code-key 类（手工加 span 包裹，
   不得改变任何字符）。
3. 面板 hover：边框变 var(--hive-400)，过渡 var(--ease-hover) 0.2s。
4. h2 标题按统一规则：六边形 SVG 图标 + 2px solid var(--hive-400) 下边框，删除编号数字。
5. 两个面板挂 .reveal，右侧面板延迟 60ms。

【保留约束】两端代码块的全部字符（命令、注释、换行）逐字保留；
h3 标题「① hive-security：架构安全验证（CLI）」「② hive-cost：成本预算与模型熔断（CostGate）」
中的①②序号可删（与 01-08 同属编号 eyebrow 清理），标题文字保留。

【回传格式】① 新的演示区 HTML（含代码逐字内容）；② 本区块 CSS；③ 改动点清单。
自查：代码内容与原文逐字一致（用 diff 工具核对）。
```

### 7.6 Stage 6：差异化四维

```text
你是字节跳动前端的资深工程师。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只改造 site/index.html 的 <section id="differentiators"> 区块，锚点 id 必须保留。

【品牌规范卡】
- 2×2 卡片网格（桌面），<=768px 单列。卡片纯白、圆角 10px、边框 var(--hairline)，
  hover 边框 var(--hive-400)。
- 每卡左上角一枚 28px 六边形角标：尖顶六边形填充，四张卡依次用
  var(--hive-300) / var(--hive-400) / var(--hive-500) / var(--hive-600) 由浅到深，
  角标内白色等宽数字 ① ② ③ ④（font-size 14px）。
- 卡片内容：加粗标题（var(--ink)，1.1rem）+ 两行卖点说明（var(--muted)，.95rem）
  + 底部证据入口小字（var(--hive-700)，等宽字体，形如 `contracts/`、`scripts/contract_lint.py`）。
- 禁：四卡同色同型（要有蓝色阶递进）；禁表格直接搬进卡片。

【本阶段契约】
1. 结构：把现有 <table> 的四行内容逐一映射为四张 .diff-card：
   ① 契约一等公民 + 防漂移（证据：contracts/、scripts/contract_lint.py）
   ② 契约级 HITL 验收回流（证据：agent_hive/、docs/card-async-hitl.md）
   ③ 架构安全验证内嵌审批关口（证据：hive_security/、benchmarks/security/）
   ④ 成本预算 + 模型熔断一等原语（证据：hive_cost/、benchmarks/cost/）。
2. 文案：卖点说明直接用原表格第三列原文（逐字），证据入口取原表格第四列前两个路径。
3. 删除原 <table>。h2 标题按统一规则（六边形图标 + 天蓝下边框，删编号）。
4. 四卡挂 .reveal，stagger 45ms 依次。
5. 深色模式下角标色阶：var(--hive-400) / var(--hive-500) / var(--hive-600) / var(--hive-700)。

【保留约束】四个维度的名称与卖点文案逐字保留；「调研实证（截至 2026-08）」引言段保留原样。

【回传格式】① 新的差异化区 HTML；② 本区块 CSS；③ 改动点清单。
自查：原表格三段文案逐字出现在卡片中、无 3 等宽卡、四卡蓝色阶递进。
```

### 7.7 Stage 7：Benchmark

```text
你是字节跳动前端的资深工程师。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只改造 site/index.html 的 <section id="benchmark"> 区块，锚点 id 必须保留。

【品牌规范卡】
- 指标条：横向大数字排版。数字用 --hive-800（深色模式 --hive-300），
  font-size 2.6rem / 字重 800 / 等宽字体；单位与小字说明 --muted .875rem。
- 指标条容器：纯白卡、圆角 10px、边框 var(--hairline)、左缘 4px solid var(--hive-400) 品牌线。
- 注释条：背景 var(--note-bg)、左边线 4px var(--note-border)、文字 var(--note-fg)，文案原样。
- 禁止：进度条/背景轨道、假仪表盘、渐变文字、数据造假（所有数字必须与原文一致）。

【本阶段契约】
1. 布局：两条 .metric-row（上下排列，间距 1rem），每条 = 左侧数字区 + 右侧说明区
   （桌面 3:7，窄屏上下堆叠）。
2. 第 1 条数字区大数字写「1.0000 / 0.0000 / 1.0000」，下方小字「检出率 / 误报率 / verdict 准确率」；
   右侧说明 = 原表格「安全验证」行结果原文（129/129 达标、avg 0.08ms / p99 0.54ms 等逐字）。
3. 第 2 条数字区大数字写「100% → 64.0% → 52.2%」，下方小字「完成率（100% / 70% / 50% 预算）」；
   右侧说明 = 原表格「成本预算」行结果原文（任务成本均值、降级/block/告警次数逐字）。
4. 删除原 <table> 与「由 benchmarks/ 确定性运行产出」段保留（原样）。
5. .note 复现命令注释条：改为第 2 条下方的品牌注释条样式，其中两个 <code> 命令原样。
6. h2 标题按统一规则。两条指标行挂 .reveal。

【保留约束】全部数字与文字逐字保留：1.0000、0.0000、129、0.08ms、0.54ms、
100.0%→64.0%→52.2%、$0.0040→$0.0026→$0.0019、0→95→85、0→37→47、0→227→217。
禁止四舍五入、禁止改写。

【回传格式】① 新的 Benchmark 区 HTML；② 本区块 CSS；③ 改动点清单。
自查：与原文数字逐字 diff 一致。
```

### 7.8 Stage 8：架构图

```text
你是字节跳动前端的资深工程师（SVG 手写能力要求高）。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只改造 site/index.html 的 <section id="architecture"> 区块内的 SVG 架构图，锚点 id 必须保留。

【品牌规范卡】
- 节点形状：尖顶六边形（pointy-top）。以圆心 (cx,cy)、外接半径 r=27 为例，六顶点 =
  (cx,cy-27) (cx+23.4,cy-13.5) (cx+23.4,cy+13.5) (cx,cy+27) (cx-23.4,cy+13.5) (cx-23.4,cy-13.5)。
- 首脑 Chief 节点：填充 var(--hive-400)，描边 var(--hive-800) 1.5px，文字纯白 15px 字重 700。
- 专家节点：填充 var(--hive-100)（深色 var(--hive-100) 已重映射为深面板色），
  描边 var(--hive-500) 1.5px，标题文字 var(--hive-800)（深色 var(--hive-300)），副标 var(--muted)。
- 连线：stroke var(--hive-500) 2px，箭头填充 var(--hive-600)。
- 画布容器 .arch-wrap：纯白/表面色背景 + 边框 var(--hairline) + 圆角 10px +
  叠加六边形点阵纹理（与 Hero 同款 data-uri，透明度 0.08）。
- 禁止：霓虹辉光滤镜、渐变节点、3D 立体阴影。

【本阶段契约】
1. 五个 <rect> 节点全部改为 <polygon> 六边形：首脑 (340,64) r=30（容纳 2 行文字）；
   四个专家 (135,174) (545,174) (135,284) (545,284) r=26。
2. 文字层序与原文一致：首脑「首脑 Chief / 定架构 · 分包 · 验收集成」，专家「编码/测试/评审/调研 + Specialist」。
   中文竖排注意：六边形内文字若溢出，把主标题 15px 副标 11px 压缩为 14px/10.5px，且必须仍可读。
3. 连线 <path> 的起点/终点调整到六边形顶点（垂直边用顶/底点，斜线用侧顶点），
   保持「Chief 向下/斜下发散到四专家」的语义不变。
4. 下方 .arch-tags 三枚徽章：圆角 999px，边框 var(--hairline)，背景 var(--surface-2)，
   hover 边框 var(--hive-400)；其中 <code> 文字色 var(--hive-700)。文字原样。
5. <svg> 的 viewBox 可微调（如 0 0 680 340 → 0 0 680 330），role="img" 与 aria-label 原样保留。
6. h2 标题按统一规则。整个 .arch-wrap 挂 .reveal。

【保留约束】aria-label 全文、四个专家名称、首脑名称与副标、三枚徽章文案原样保留；
连线语义（谁指向谁）不变。

【回传格式】① 新的架构区 HTML（含完整 SVG）；② 本区块 CSS；③ 改动点清单。
自查：六边形节点无文字溢出、箭头指向与原图一致、深色模式可读。
```

### 7.9 Stage 9：快速开始 + 安全

```text
你是字节跳动前端的资深工程师。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只改造 site/index.html 的 <section id="quickstart"> 与 <section id="security">
两个区块，锚点 id 必须保留。

【品牌规范卡】
- 浅色代码面（quickstart 代码块）：与演示区同一 .code-panel 规范（--code-bg 底、
  --code-border 边框、三色代码着色：墨/灰/天蓝、顶部终端栏三浅蓝点）。
- 安全列表：五条 <li>，左侧 10px 天蓝六边形项目符（clip-path 六边形，背景 var(--hive-400)，
  margin-right .6rem，vertical-align 基线微调）；列表文字 var(--ink)，
  行内 <code> 用 var(--code-bg) 底 + var(--code-border) 边框。
- 安全区外围：极浅边框卡片（1px var(--hairline)，背景 var(--surface)，圆角 10px，内边距 1.5rem）。
- 禁：进度条、超大彩色圆点、左右图文分栏。

【本阶段契约】
1. quickstart：代码面板标题写「安装与运行」；代码 6 行逐字保留（含中文注释）；
   面板下方段落「更详细的 CLI 参数…」原样，其中两个链接颜色 var(--hive-700)。
2. security：五条 <li> 文案逐字保留；「本站零遥测」「CLI 默认不执行命令」两条开头保留 <strong>；
   列表外层包 .security-card 卡片容器。
3. 两节 h2 标题均按统一规则（六边形图标 + 天蓝下边框 + 删编号）。
4. quickstart 面板与 security 卡片均挂 .reveal（security 延迟 60ms）。
5. 深色模式：六边形项目符颜色切换为 var(--hive-500)。

【保留约束】两个 <code> 命令字面量（--allow-danger、rm -rf 等）、「检查范围/未覆盖范围」
全部文字、链接 URL 原样保留。

【回传格式】① 两节新 HTML；② 本区块 CSS；③ 改动点清单。自查：五条安全声明逐字一致。
```

### 7.10 Stage 10：FAQ + 页脚深色带

```text
你是字节跳动前端的资深工程师。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段只改造 site/index.html 的 <section id="faq"> 区块（锚点 id 保留）与 <footer>
的视觉样式（页脚 HTML 结构在 Stage 2 已换新，若尚未完成则按 Stage 2 契约一并交付）。

【品牌规范卡】
- 手风琴 details.faq：背景 var(--surface)，边框 1px var(--hairline)，圆角 8px，
  间距 .6rem；展开态（[open]）边框 var(--hive-400) 且左侧 3px var(--hive-400) 品牌线。
- summary：padding .7rem 1rem，字重 600；marker 颜色 var(--hive-500)；
  hover 背景 var(--hive-50)。
- 展开动画：.faq-body 由 display:none 改为 grid-template-rows 0fr→1fr 过渡
  （transition: grid-template-rows .24s var(--ease-out)），reduced-motion 时关闭动画。
- 页脚：深海军蓝渐变带 var(--hive-900)→var(--hive-800)（135deg），
  白字版权行 + rgba(255,255,255,.78) 零遥测声明行，链接色 #A9D1E8。

【本阶段契约】
1. 五个 <details class="faq"> 的问题与答案文案逐字保留（含 <code> 内容）。
2. 每个 summary 前加 12px 六边形图标（浅蓝描边，aria-hidden）。
3. 展开态样式按品牌卡实现。
4. footer 两段文字逐字保留，样式按品牌卡实现（若 Stage 2 已交付新页脚则跳过本项，
   并在回传中注明「页脚已由 Stage 2 完成」）。
5. 每个 details 挂 .reveal（stagger 45ms，最多 4 级后不再延迟）。

【保留约束】五问五答全文、页脚版权与零遥测声明逐字保留；不新增 FAQ 条目。

【回传格式】① FAQ 新 HTML；② 本区块 CSS；③ （如涉及）页脚 CSS；④ 改动点清单。
```

### 7.11 Stage 11：PWA 资产（图标 / manifest / sw.js / theme-color）

```text
你是字节跳动前端的资深工程师（PWA 与图像处理）。工作目录：C:\Users\10104\Desktop\code\agent-hive。
本阶段处理新 logo 的 PWA 图标资产与三处元信息，不涉及页面主体样式。

【输入素材】C:\Users\10104\Desktop\code\agent-hive\assets\logo.webp（800×800，
近白底 #F7F8F8 + 天蓝蜂巢 #82B9DE/#7DB9E0 主体，无文字）。用任意本机图像工具
（ImageMagick/Pillow 等）从它生成以下文件，覆盖 site/icons/ 旧绿色图标：

【图标清单（尺寸精确）】
1. site/icons/favicon-32.png        32×32   主体居中，占画布 88%，导出 PNG
2. site/icons/apple-touch-icon.png  180×180 主体居中，占画布 90%，不透明（iOS 会自行圆角）
3. site/icons/icon-192.png          192×192 主体居中，占画布 88%
4. site/icons/icon-512.png          512×512 主体居中，占画布 88%
5. site/icons/icon-maskable-512.png 512×512 遮罩安全版：纯色 #7DB9E0 满底，
   蜂巢主体（裁掉原图底色后）等比缩放至画布中心 56%-60% 安全区
   （safe zone：内容必须落在以画布中心为圆心、半径 40% 的圆内）
生成规则：从 webp 解码 → 去底色（把近 #F7F8F8 像素转透明，容差 ±10）→ 等比缩放至目标占比
→ 居中 → 保存 PNG。若蜂巢主体因去底色出现杂边，用 1px 羽化。

【manifest.webmanifest】改 3 处：
1. "theme_color" 改 "#7DB9E0"，"background_color" 改 "#F7F8F8"；
2. icons 数组替换为 5 个条目（favicon 不加 purpose，icon-192/icon-512 purpose "any"，
   icon-maskable-512 purpose "maskable"）；sizes 与路径与上面一致；
3. 其余字段原样。

【index.html】改 3 处（仅 meta/head，不动正文）：
1. <meta name="theme-color"> 改为双条：light 用 "#7DB9E0"、dark 用 "#0F1B26"，
   写法 <meta name="theme-color" content="#7DB9E0" media="(prefers-color-scheme: light)">
   与 <meta name="theme-color" content="#0F1B26" media="(prefers-color-scheme: dark)">；
2. 补一行 maskable 图标声明
   <link rel="manifest" href="./manifest.webmanifest"> 保持不变；
3. <title> 与 <meta name="description"> 保持原文案不动。

【sw.js】PRECACHE_URLS 缓存清单里加入：'./logo.webp' 与 './icons/icon-maskable-512.png'；
确认其余缓存条目与 index.html/manifest/4 个旧图标路径一致；CACHE_VERSION 自增（如 'v1' → 'v2'）。

【回传格式】① 5 个 PNG 的生成命令（含参数）或脚本；② manifest.webmanifest 全文；
③ index.html 中 3 处改动 diff；④ sw.js 改动 diff；⑤ 自查：5 张图标文件大小与尺寸清单。
```

### 7.12 Stage 12：整页组装 + 总验收

```text
你是字节跳动前端的资深工程师。工作目录：C:\Users\10104\Desktop\code\agent-hive。
前序各阶段分别产出了 10 个分节的 HTML/CSS 片段（存放在 site/_rebrand_scratch.md，
按 Stage 2-10 编号标注）。本阶段把它们组装为最终的 site/index.html 完整文件。

【品牌规范卡】（终检版，组装后按此卡逐项过检）
- 浅色变量、深色变量、字体栈、六边形使用规则、动效规范：以 site/_rebrand_scratch.md
  中 Stage 2 的「全局基础层」为准（它是单一事实源）。
- 红线：无 --green-* 残留、无纯黑 #000、无外链字体/脚本/CSS、无霓虹辉光、
  无三张等宽卡、无编号 eyebrow（01-08 与 ①② 序号均已删）、琥珀色 #EBA22C 只出现在品牌字标蜂点。

【组装规则】
1. 保留 <!DOCTYPE html>/<head> 骨架、meta 标签（含 Stage 11 的 theme-color 双条）、
   manifest 与图标 link、<body> 内 nav → header.hero → main（8 个 section 按原顺序）→ footer。
2. 各 section 的最终 HTML 以 scratch 中对应 Stage 产物为准，但锚点 id 必须与原文件逐一对应：
   #top #download #demo #differentiators #benchmark #architecture #quickstart #security #faq。
3. <style>：Stage 2 基础层在前，各节 CSS 依节序合并；重复定义以最后出现的为准；
   合并后删除注释掉的旧样式残留。
4. <script>：入场动效 IntersectionObserver 脚本放 </body> 前，Service Worker 注册脚本
   原样保留（位置不变）。合并后不得出现两个 IntersectionObserver 定义。
5. 删除组装过程中产生的临时注释；最终文件编码 UTF-8（无 BOM）。

【终检清单（在回传中逐项打勾报告）】
□ 9 个锚点全部存在且导航可跳转；□ 全部外链 URL 与原版一致（diff 核对）；
□ 正文文案与原版逐字一致（除已批准的编号删除与面板标题）；□ 无 --green-* / #14532d 残留；
□ 深色模式（prefers-color-scheme: dark）下正文/卡片/代码面板对比度合格；
□ <=768px 窄屏：卡片单列、代码面板单栏、无横向滚动条；□ prefers-reduced-motion 时入场动画关闭；
□ 网络面板无本域外资源请求（shields.io 徽章除外）；□ 图标 5 文件引用路径正确；
□ 无纯黑 #000；□ 六边形元素只出现在 4 个允许位置；□ 琥珀色只出现在字标蜂点。

【回传格式】① 最终完整 site/index.html 全文（一个代码块）；② 终检清单打勾结果；
③ 与你本机原版 index.html 的 diff 摘要（按节列出改动范围，非全文 diff）。
```

---

## 8. 总验收门禁（Stage 12 回传后你亲自执行）

```bash
cd C:\Users\10104\Desktop\code\agent-hive

# 1. 锚点与文案抽样 diff（除批准改动外应无差异）
git diff --word-diff site/index.html | Select-String "^-"   # 逐条人工确认都是批准的改动

# 2. 打开页面人工走查（双击 site/index.html 或 python -m http.server 8000 后访问）
#    - 9 个导航锚点全部可跳；徽章 4 张图可显示
#    - F12 Network：除 shields.io 外无任何外部请求（零遥测红线）
#    - 切系统深色模式：正文/卡片/代码面板全部可读
#    - 缩到 375px 宽：无横向滚动；DevTools 模拟 prefers-reduced-motion 验证动画关闭

# 3. 图标与 PWA
#    - icons/ 下 5 个 PNG 尺寸正确（favicon-32 / apple-touch-icon 180 / 192 / 512 / maskable-512）
#    - Lighthouse PWA 检查：manifest 可解析、maskable 图标存在、theme-color 匹配

# 4. 提交（分节提交，便于回滚）
git add -A && git commit -m "style(site): rebrand to hive-blue logo theme"
git push origin main
```

任何一条不过：把失败现象原样发回给对应 Stage 的 flash 提示词，让它修复重跑；不得手改后谎报。

---

## 9. 常见问题与注意点

1. **logo 引用路径**：GitHub Pages 只发布 `site/` 目录，因此官网用 `./logo.webp`（Stage 3 前置步骤已把 `assets/logo.webp` 复制为 `site/logo.webp`）；README 在根目录，写 `assets/logo.webp`。flash 容易把相对路径写错，Stage 12 终检时重点核对。
2. **深色模式的「浅蓝」变量**：`--hive-100` 在深色下被重映射为深面板色，flash 若在深色媒体查询里重新定义浅色值会破坏对比度，遇此情况回滚该行即可。
3. **代码面板着色**：只允许 墨/灰/天蓝 三色；flash 常会顺手加绿色字符串色（旧主题习惯），发现即要求去掉。
4. **编号 eyebrow 清理范围**：仅删「01-08」数字与「①/②」h3 序号，节标题文字、表格内 ①②③④（差异化四维名称中的编号保留）、Benchmark 数字一律不动。
5. **每阶段只给一节**：一次只发一个 Stage 提示词；把两个 Stage 合并进一次对话会让 flash 串味。分节产物先存 `site/_rebrand_scratch.md`，最后 Stage 12 才组装。
6. **README 联动**：本计划完成官网改版后，README 顶部 logo 横幅（`assets/logo.webp`）与官网 Hero 使用同一素材，视觉天然一致；README 已先行按同一品牌卡升级（见 README.md / README_EN.md）。
