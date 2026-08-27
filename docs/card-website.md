# 卡片：agent-hive 官网建设（card-website）

> 批次状态：待审批（本卡片为完整方案设计，批准后按批次派发实现）
> 依赖：站点骨架批次（W1 site-foundation）无硬依赖，可独立启动；安全中心（WEB-04）与安全 Demo（WEB-12）依赖 `docs/deepsec-security-extension.md` 的 SEC 卡片落地，属于二期或与 SEC 批次联动
> 规模：L；优先级：1；轮次上限：3
> 交付模式：站点内容复用仓库文档（README/SECURITY/docs），建立「文档单一事实源 + 漂移检查」，延续 `scripts/generate_contracts.py --check` 的防漂移哲学

---

## 1. 背景与目标

agent-hive 是一个"首脑统筹的多智能体编排框架"（Python ≥3.11、uv、LangGraph、DSH skill 与 CLI 双宿主），当前已有 267 项回归测试（`uv run pytest -q`）、完整安全模型（SECURITY.md）与 9 张生产级补充卡片（cost-control/model-resilience/async-hitl/tool-registry/streaming/prompt-management/multi-tenancy/distributed-engine/data-compliance）+ card20 系列，但**没有任何对外展示站点**：仓库即文档，缺少产品化门面。

本卡片目标是建设一个**专用项目官网**，承担四件事：

1. **展示优势**：首脑协议、契约先行、评估-优化回路、守卫规则、依赖感知 fan-out、整体集成守卫、项目看板、权限分层 T0/T1/T2、成本可观测、断点续跑——每项都有独立可读页面。
2. **安全验证可视化**：把 SECURITY.md、安全审计与漏洞修复报告（`agent-hive-审计与研发建议.md`、`漏洞修复报告.md`、`漏洞修复文档.md`）转化为可浏览的「安全中心」，并内置**守卫拦截案例库**（危险命令、路径逃逸、密钥剔除的真实拦截样例回放）。
3. **架构与演示**：用可交互图讲清 graph / scheduler / integration / paths 分层；用**脱敏的运行回放**演示真实看板状态机，无需任何 LLM 密钥即可"看到引擎在跑"。
4. **强 GitHub 集成**：GitHub Pages 托管、徽章与仓库元数据、路线图与更新日志自动同步、edit-on-GitHub、Issue/讨论/Release/安全公告一站式入口。

非目标（本卡片明确不做）：

- 不重写核心引擎、不新增产品功能；
- 不做需要用户密钥的"在线真实运行"（演示一律无密钥回放）；
- 不做重型 SPA 与复杂登录体系（第一期为纯静态站点）；
- 不承诺多语言全覆盖（第一期以中文为主，英文为二期）。

---

## 2. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 站点生成 | **MkDocs + Material for MkDocs** | 与 Python 后端同栈、零前端构建链；内置客户端搜索（无后端、隐私友好）、代码高亮、Mermaid 图、多语言与 i18n、GitHub Pages 一等公民；可 `--strict` 构建 |
| 首页/落地页 | MkDocs 自定义主页模板 + 少量原生 CSS/JS | 不引入框架即可实现 hero、特性网格、徽章墙、CTA；避免 SPA 复杂度 |
| 交互演示 | 静态优先：Mermaid 交互图 + 预录 JSON 轨迹的前端回放（看板状态机动画、守卫拦截案例） | 纯静态即可承载"演示"，无服务器、无密钥、可离线审计 |
| 可选演示服务（第二阶段） | **FastAPI**（Python 同栈），仅暴露只读/纯函数接口：调度器纯函数沙盒、run 回放数据、契约漂移检查（复用 `scripts/generate_contracts.py` 核心逻辑） | 演示"真实引擎"而不暴露任何命令/密钥；后续如做在线沙盒，这是唯一需要后端的部分，且可独立部署 |
| 徽章/元数据 | shields.io（静态徽章 + GitHub Actions 动态徽章） | 零自建服务 |
| 版本与依赖 | uv + `uv.lock` 锁定，`hatchling` 构建 | 与仓库一致 |
| 备选（不推荐首期） | Astro/Next.js 独立营销页 | 引入 Node 工具链，与"Python 优先"定位相悖；仅当未来需要高级交互时再评估 |

设计约束：运行时默认**零第三方脚本 CDN**（字体、图标本地化），站点无 JavaScript 依赖也能完整阅读——既利于隐私，也利于中国网络环境可访问。

---

## 3. 站点信息架构与路由

| 路由 | 页面 | 内容来源 |
|---|---|---|
| `/` | 首页：定位一句话、特性六宫格、实时徽章、架构缩略图、看板状态机缩略演示、CTA（快速开始/看源码） | README 提炼 + 徽章 |
| `/features/` | 特性详解：首脑协议、契约先行、评估-优化回路、守卫规则、依赖感知 fan-out、整体集成、项目看板、权限分层 T0/T1/T2、派发资格评审、成本可观测、断点续跑 | README + 卡片文档 |
| `/architecture/` | 架构：分层图、`graph.py`/`scheduler.py`/`integration.py`/`paths.py`/`chief.py`/`specialists.py` 职责卡、数据流、状态机、双宿主（DSH skill 与 CLI）说明 | docs/architecture-card20.md + 源码导读 |
| `/security/` | 安全中心：渲染 SECURITY.md、信任边界、五类防护（密钥/命令/文件/提示词注入/集成）、审计与漏洞修复报告、报告漏洞流程 | SECURITY.md + 三份安全文档 |
| `/docs/` | 文档中心：快速开始、CLI 参数、.env 配置、契约说明、技能安装、断点续跑、验证命令 | README + skill/contracts.md |
| `/demos/` | 演示区：① Run Replay 运行回放 ② 看板/状态机模拟器 ③ 契约漂移检查 playground ④ 守卫拦截案例库 ⑤ 架构交互图 | CI 生成的脱敏数据 + 静态案例 |
| `/roadmap/` | 路线图：9 张生产级补充卡片（async-hitl、cost-control、streaming、multi-tenancy、distributed-engine、model-resilience、prompt-management、tool-registry、data-compliance）+ DeepSec 安全增强扩展（SEC 系列，planned）状态化呈现 | docs/card-*.md + GitHub Issues 标签快照 |
| `/changelog/` | 更新日志：GitHub Releases 自动同步 | GitHub API 构建期快照 |
| `/community/` | 社区与贡献：CONTRIBUTING、Discussions、贡献者墙、联系 | GitHub 链接集 + 贡献者快照 |
| `/privacy/` | 隐私政策：统计方式、无 cookie、退出机制 | 静态撰写 |
| `/search/`、`/404.html` | 搜索与 404 | MkDocs 内置 / 自定义 |

每页页脚提供 **Edit on GitHub** 直达源文件；所有 GitHub 深链集中在 `/community/` 与页脚。

---

## 4. 内容模型

采用 MkDocs YAML front matter + `nav` 权重，形成可校验的内容模型：

| 字段 | 说明 |
|---|---|
| `title` / `description` | 标题与摘要（用于 SEO og 标签） |
| `lang` | `zh` 主语言；`en` 二期 |
| `date` | 页面更新日期 |
| `card_id` | 关联演进卡片 id（如 `async-hitl`），用于路线图自动归组 |
| `tags` | 特性/架构/安全/演示 等分类 |
| `source` | 内容源文件相对路径（README/SECURITY/docs/xxx），供漂移检查 |
| `github_edit` | Edit on GitHub 相对路径 |
| `audit` | 关联的安全审计/修复报告路径 |

文档类型：`landing`（首页）、`feature`（特性）、`architecture`、`security`、`tutorial`（教程）、`reference`（参考）、`card`（演进卡片）、`roadmap`、`changelog`、`privacy`。

**单一事实源规则**：站点页面原则上**生成或渲染自仓库文档**，而不是复制粘贴。README、SECURITY.md、`skill/contracts.md`、`docs/card-*.md` 是权威源；站点构建时做「站点 ↔ 仓库文档」漂移检查（沿用 `generate_contracts.py --check` 模式），漂移即 CI 失败。

---

## 5. GitHub 集成（API 与链接）

### 5.1 链接集（无 token，静态深链）

仓库主页、Issues、Discussions、Releases、Actions、Security 标签页（Advisories/Dependabot）、Contributors、License、Star 按钮、`Yingjiacheng7651010/agent-hive` 全量入口统一放页脚与 `/community/`。

### 5.2 GitHub REST API 使用策略

**原则：构建期抓快照，运行时零 API 调用**（避免限流、避免前端 token、保证静态托管可行）：

| 数据 | API | 获取时机与方式 |
|---|---|---|
| Star/Fork/Issue 计数 | `GET /repos/{owner}/{repo}` | CI 构建期抓取 → 生成 `site_data/repo.json`，首页徽章引用 |
| 贡献者 | `GET /repos/{owner}/{repo}/contributors` | 构建期快照（头像 + 用户名），仅存 URL 与名字 |
| Releases 更新日志 | `GET /repos/{owner}/{repo}/releases` | 构建期快照 → `/changelog/` |
| 路线图 Issues | `GET /search/issues?q=repo:... label:roadmap` | 构建期快照 → `/roadmap/` 状态化 |
| 运行回放数据 | 仓库内 `site_data/runs/*.json`（CI 从脱敏 run 产物生成） | 随仓库提交，随 Pages 部署 |

动态徽章（CI 状态、测试数、最近提交）走 shields.io 的 GitHub Actions/静态端点，运行时无 token。

### 5.3 CI 内凭据

- Pages 部署用 `GITHUB_TOKEN`（`actions/deploy-pages` 所需最小权限）；
- 如需抓取私有仓库元数据或写 Release，用 **fine-grained PAT，最小仓库权限**，存仓库 Secrets；
- 站点仓库内**绝不允许任何真实密钥**；演示数据生成管线负责脱敏（见 §8）。

---

## 6. CI/CD

| 工作流 | 触发 | 内容 |
|---|---|---|
| `ci.yml` | push / PR | uv sync → ruff → pytest（当前 267 全量）→ compileall → 契约漂移 `generate_contracts.py --check` → markdownlint → 链接检查 → MkDocs `--strict` 构建 → 上传构建产物 |
| `pages.yml` | main 分支 | 构建站点（zh）→ `actions/configure-pages` + `upload-pages-artifact` + `deploy-pages` 发布 GitHub Pages |
| `release.yml` | tag `v*` | hatchling 构建 sdist/wheel → （可选）发布 PyPI → 依据 conventional commits 生成更新日志 → 创建 GitHub Release（自动填充 CHANGELOG 并同步 `/changelog/` 快照） |
| `security.yml` | 定时/依赖变更 | Dependabot（pip/uv + github-actions）+ CodeQL（Python + 站点 JS）+ gitleaks 密钥扫描 |
| `quality.yml` | push / PR | Lighthouse CI（性能/无障碍/最佳实践阈值）+ axe 无障碍扫描（见 §8） |
| `demo-data.yml` | 定时（如每周） | 重新生成脱敏 run 回放快照与路线图快照 → 开 PR 更新 `site_data/` |

分支保护：main 仅允许 PR 合入，必检项 = ci + pages 构建 + quality；提交签名（可选但推荐）。

---

## 7. 安全（含安全验证可视化）

### 7.1 站点自身安全

- 纯静态、无密钥、无运行时第三方脚本；GitHub Pages 强制 HTTPS；
- 静态资源完整性：自托管字体/图标/JS，禁用远程脚本；如加 CSP 头则全站覆盖；
- 站点仓库同样纳入 gitleaks + 依赖审计，依赖数量最小化（MkDocs 插件白名单）。

### 7.2 安全中心（对外展示"安全验证"）

| 子页 | 内容 |
|---|---|
| 安全模型 | 渲染 SECURITY.md：五类防护逐一配图（密钥剔除 `_safe_env`、路径围栏 `paths.py`、命令默认禁用 + 危险片段拦截 + 120s 超时、提示词注入按不可信数据处理、staging 原子集成） |
| 审计与修复 | 展示 `agent-hive-审计与研发建议.md`、`漏洞修复报告.md`、`漏洞修复文档.md` 的结论摘要与逐项修复对照表 |
| 信任边界 | 明确"本机用户权限/非沙箱、SQLite 单机、非 Python 交付物只做结构校验"等已知边界，不粉饰 |
| DeepSec 安全增强 | 二期页面：展示 `docs/deepsec-security-extension.md` 的 SEC 系列落地状态（扫描/ScopeManifest/SARIF/门禁）；**未落地前必须标注 planned，不得宣称已具备**，并注明"仅借鉴 DeepSec 公开思想，未复制其源码" |
| 报告漏洞 | 引导至 GitHub **私有漏洞报告**（Private Vulnerability Reporting），声明"不公开利用细节" |

### 7.3 可选演示服务（FastAPI，二期）安全要求

- 无 LLM 密钥、无命令执行接口（继承"守卫"哲学：只读/纯函数）；
- 入参 pydantic 校验；限流（IP 级）；CORS 白名单；请求超时；审计日志不含 PII；
- 依赖最小化 + `uv pip audit`；独立部署、与主站网络隔离。

### 7.4 供应链

uv.lock 锁定依赖、Dependabot 周更、发布物签名（可选）、站点插件与主题版本固定。

---

## 8. 无障碍（Accessibility）

目标 **WCAG 2.1 AA**，具体措施：

- 语义化：landmark（header/nav/main/footer）、标题层级、跳转链接、focus 可见样式；
- 图片/图标：alt 文本；图标按钮带 aria-label；
- 交互演示：全部键盘可操作、焦点陷阱为零；动画（看板状态机、fan-out 动效）尊重 `prefers-reduced-motion`，并提供静态文字版步骤说明；
- Mermaid 架构图：提供 `aria-label`/描述文本 + 可展开的文字版（屏幕阅读器可读）；
- 搜索：MkDocs 内置搜索支持键盘；表单标签完整；
- 对比度：主题自定义遵循 4.5:1；400% 缩放下不丢信息；`lang` 属性正确（zh）；
- 自动化门禁：axe-core（pa11y）扫描 **0 critical / 0 serious**；Lighthouse CI 无障碍 ≥ 90；
- 手动检查清单：键盘走查、屏幕阅读器抽样（NVDA/VoiceOver）、缩放走查——列入上线验收。

---

## 9. 分析与隐私（Analytics / Privacy）

- **默认零遥测**：站点不带任何第三方追踪；把"本地部署、零遥测"作为产品卖点写进首页与隐私页；
- 若需访客统计：自托管 **Plausible 或 Umami**（单像素、无 cookie、IP 匿名化、可自部署到国内可达位置），禁用一切跨站 cookie；
- 尊重 `DNT` 并提供页脚显式退出（关闭统计像素）；
- `/privacy/` 页面声明：统计什么、不统计什么、保留期、无广告、无第三方共享；
- 演示区数据均为静态快照，无客户端上报；可选 FastAPI 演示服务的访问日志最小化且不含 PII，明确保留期。

---

## 10. 演示（Demos）

| 演示 | 形式 | 说明 |
|---|---|---|
| ① Run Replay 运行回放 | 前端播放 CI 预生成脱敏轨迹 JSON | 从真实 run 产物（`runs/<run_id>/` 的看板状态、cost.json、final_report.md）脱敏生成；回放"待派发→进行中→待验收→通过/返工→熔断/阻塞"状态机与 fan-out 时序 |
| ② 看板模拟器 | 客户端原生 JS | 用户可点选"返工/熔断"观察状态传播，理解评估-优化回路 |
| ③ 契约漂移检查 playground | 复用 `generate_contracts.py` 核心逻辑（只读） | 上传/粘贴契约片段，演示漂移如何被发现（无服务器时用预置样例） |
| ④ 守卫拦截案例库 | 静态案例 + 回放 | 展示真实拦截：`rm -rf` 片段拒绝、`..` 路径逃逸拒绝、密钥变量被剔除、危险目标需 `--allow-danger` |
| ⑤ 架构交互图 | Mermaid + 放大查看 | 分层架构与数据流，点击跳转对应源码导读页 |

所有演示**不需要 API 密钥、不执行命令**——这是演示区的硬约束。

---

## 11. 测试策略

| 层级 | 工具 | 覆盖 |
|---|---|---|
| 内容质量 | markdownlint、lychee/mlinks 链接检查、拼写（可选） | 所有页面、全部外链/锚点、front matter 必填字段 |
| 构建门禁 | MkDocs `--strict` | 坏链接、缺失文件、模板错误直接失败 |
| 漂移检查 | 自研脚本（仿 `generate_contracts.py --check`） | 站点页面 ↔ README/SECURITY/docs 内容一致性 |
| 单元（演示服务，二期） | pytest + TestClient | 限流、pydantic 校验、CORS、错误处理 |
| E2E 冒烟 | Playwright | 导航、搜索、回放演示、404、多语言切换 |
| 无障碍 | axe + Lighthouse CI | §8 阈值 |
| 安全扫描 | gitleaks、bandit（演示服务）、uv pip audit、ZAP 基线（可选） | 无密钥泄漏、依赖无已知漏洞 |
| 性能预算 | Lighthouse CI | LCP < 2.5s、CLS < 0.1、无阻塞第三方脚本 |

---

## 12. 部署

| 项 | 方案 |
|---|---|
| 主托管 | **GitHub Pages**（HTTPS、零运维、与仓库同组织、Actions 自动部署） |
| 域名 | 可选 `docs.agent-hive.dev` 或 `agent-hive.dev`；CNAME + DNS 记录；一期可先用 `*.github.io` |
| 环境 | main → 生产 Pages；PR → 构建产物预览（可选接 Netlify/Cloudflare Pages 预览部署） |
| 可选演示服务 | Docker 容器化 FastAPI，部署于任何 PaaS/VM；与静态站解耦，未部署时演示降级为纯静态回放 |
| 上线资产 | favicon、og 标签、sitemap.xml、robots.txt、自定义 404、站点 logo（蜂群主题） |

---

## 13. 工作包分解（批次与派发顺序）

### 批次 1：site-foundation（站点骨架）
- **目标**：可构建、可部署的 MkDocs 站点骨架。
- **接口契约**：`mkdocs.yml` 提供 nav/主题/多语言/i18n/搜索配置；自定义首页模板；GitHub Pages 部署工作流。
- **expected_output**：`mkdocs.yml`、站点目录（`site/` 源）、`docs-site/` 或根目录 `docs_site/` 独立目录、`pages.yml`、`ci.yml`。
- **depends_on**：`[]`
- **验收标准**：`mkdocs build --strict` 零错误；`pages.yml` 部署成功且 HTTPS 可访问；首页五区块（hero/特性/徽章/架构缩略/CTA）呈现；中文 `lang` 正确。
- **交付物**：`site/` 骨架 + 两个工作流。
- size：M；priority：1；轮次上限：3

### 批次 2：content-migration（内容迁移与内容模型）
- **目标**：把 README/SECURITY/docs 变为站点页面，建立单一事实源与漂移检查。
- **接口契约**：front matter 内容模型；页面 ↔ 源文件映射表；漂移检查脚本。
- **expected_output**：/features、/architecture、/security、/docs、/roadmap、/community 全部页面；安全中心渲染三份安全文档；链接与 markdownlint 门禁。
- **depends_on**：`[site-foundation]`
- **验收标准**：全部目标路由 200；Edit on GitHub 直达源文件；漂移检查能捕获"站点与仓库文档不一致"；外链零死链。
- **交付物**：站点内容目录 + 漂移脚本 + 文档映射表。
- size：L；priority：1；轮次上限：3

### 批次 3：demos-github（演示与 GitHub 集成）
- **目标**：上线演示区与 GitHub 数据管线。
- **接口契约**：`site_data/` 快照格式（repo.json / releases.json / roadmap.json / runs/*.json 脱敏轨迹）；回放播放器接口（仅读 JSON）。
- **expected_output**：五个演示（§10）、徽章墙、/changelog、路线图状态化、贡献者墙、`demo-data.yml` 定时快照。
- **depends_on**：`[content-migration]`
- **验收标准**：回放演示在无密钥、断网（除页面自身）下可完整播放；构建期 API 快照无 token 依赖；脱敏检查（gitleaks + 人工）通过；徽章显示真实 CI/测试状态。
- **交付物**：演示组件 + 快照管线 + 快照数据。
- size：L；priority：2；轮次上限：3

### 批次 4：quality-launch（质量门禁与上线）
- **目标**：无障碍、隐私、性能、安全门禁齐备并正式上线。
- **接口契约**：Lighthouse CI 阈值配置；axe 扫描接入；隐私页与退出机制；上线检查清单。
- **expected_output**：quality.yml、/privacy、sitemap/robots/og/favicon、自定义域名（可选）、上线验收报告。
- **depends_on**：`[demos-github]`
- **验收标准**：axe 0 critical/serious；Lighthouse 性能/无障碍/最佳实践达标；隐私声明与实现一致；§14 验收清单全部通过。
- **交付物**：门禁配置 + 上线资产 + 验收报告。
- size：M；priority：3；轮次上限：3

### 批次 5（可选，二期）：demo-api（FastAPI 演示服务）
- **目标**：可选的在线 playground（调度器纯函数沙盒、契约漂移在线检查）。
- **接口契约**：只读/纯函数 API；限流与校验；无密钥、无命令执行。
- **expected_output**：独立 `demo_api/` 服务 + Dockerfile + pytest 测试 + 部署文档。
- **depends_on**：`[quality-launch]`
- **验收标准**：pytest 全绿；限流/校验/CORS 用例通过；bandit 与 uv pip audit 干净；未部署时主站降级为纯静态演示。
- **交付物**：`demo_api/` + 容器化配置。
- size：M；priority：4（二期）；轮次上限：3

---

## 14. 总体验收标准（上线门槛）

**内容与展示**
- [ ] 全部路由（§3）可访问且无死链；`mkdocs build --strict` 零错误；
- [ ] 12 项核心特性各有独立可读页面（优势展示完整）；
- [ ] 安全中心渲染 SECURITY.md 与三份安全文档，信任边界如实标注；
- [ ] 演示区五演示全部可用，硬约束成立：**无密钥、不执行命令**；
- [ ] 站点与仓库文档零漂移（漂移检查通过）。

**GitHub 集成**
- [ ] Pages 自动部署绿；徽章显示真实 CI 状态与测试数；
- [ ] /changelog 与 Releases 同步、/roadmap 与 Issues 标签同步；
- [ ] Edit on GitHub 全部可达；gitleaks 扫描干净（仓库无任何密钥泄漏）。

**CI/CD 与安全**
- [ ] ci/pages/release/security/quality 五个工作流全部通过；
- [ ] Dependabot + CodeQL 已启用；依赖审计无已知高危漏洞；
- [ ] 可选演示服务（若实现）通过限流/校验/CORS 测试与 bandit 扫描。

**无障碍、分析与隐私**
- [ ] axe 扫描 0 critical / 0 serious；Lighthouse 无障碍 ≥ 90；
- [ ] 键盘走查、屏幕阅读器抽样、400% 缩放走查通过；
- [ ] 无第三方追踪默认关闭；隐私页与实现一致；退出机制可用。

**性能与部署**
- [ ] Lighthouse 性能 ≥ 90（LCP < 2.5s、CLS < 0.1）；无阻塞第三方脚本；
- [ ] 上线资产齐全（favicon/og/sitemap/robots/404）；域名解析正确（如启用）。

---

## 15. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 站点与仓库文档漂移 | 单一事实源 + 构建期漂移检查（CI 失败），延续契约漂移模式 |
| GitHub API 限流 / token 暴露 | 构建期快照、运行时零 API、token 最小权限存 Secrets |
| 演示误被当作"在线真实运行" | 页内显著标注"无密钥回放演示"；硬约束 + 验收门槛 |
| i18n 维护成本 | 第一期仅中文；英文作为二期独立批次，不阻塞上线 |
| Pages 部署受组织策略限制 | 预留 Netlify/Cloudflare Pages 备选；工作流与构建解耦 |
| 自定义主题破坏无障碍 | axe + Lighthouse CI 门禁 + 手动走查列入上线清单 |

---

## 16. 落地顺序与里程碑

1. **M1（批次 1）**：骨架可构建、Pages 可访问 —— 1 个批次；
2. **M2（批次 2）**：内容全量上线、漂移检查生效 —— 2 个批次；
3. **M3（批次 3）**：演示与 GitHub 数据管线可用 —— 3 个批次；
4. **M4（批次 4）**：质量门禁齐备、正式对外发布 —— 4 个批次；
5. **M5（二期，批次 5）**：可选在线 playground —— 单独审批。

每批次沿用仓库既有流程：首脑分包 → 契约化工作包 → 审批 → 派发 → 验收评审 → 集成；验收不通过自动带反馈返工，满 3 轮熔断。
