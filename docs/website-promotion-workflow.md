# agent-hive 项目官网与 GitHub 推广工作流

> 版本：v1.0 | 状态：待架构审批
> 目标：建设一个可部署、可维护、与 GitHub 强关联的项目官网，展示 agent-hive 的工程能力、安全增强能力和可验证证据。

## 1. 产品定位

官网不是简单 README 镜像，而是“产品说明 + 可验证 Demo + 文档入口 + GitHub 社区入口 + 安全透明页”的统一门户。

核心传播语句：

> agent-hive：以首脑统筹、契约驱动、依赖感知并发、评估-优化回路和安全发布门禁为核心的生产级多智能体编排框架。

不得使用未经证实的绝对性表述，例如“绝对安全”“100% 无漏洞”“完全符合 GDPR”。改用“已覆盖的检查范围、测试证据和明确边界”。

---

## 2. 推荐技术方案

### MVP

- 前端：静态站点优先，React/Vite 或 Next.js 静态导出。
- 样式：Tailwind CSS 或项目统一 CSS token。
- 内容：Markdown/MDX，架构、卡片、API 和安全报告可复用仓库文档。
- 部署：GitHub Pages、Cloudflare Pages 或 Vercel 任选其一。
- GitHub 数据：优先使用公开链接和 shields；动态 API 必须缓存并处理 rate limit。

### 服务化阶段

- 增加只读 API：项目健康度、最新 release、测试证据、公开安全基线。
- 不在官网服务端暴露 DeepSeek/Tavily/API Key。
- Demo 使用脱敏 fixture 或静态录制，不让访客触发任意命令执行。

---

## 3. 网站页面卡片

## WEB-01：首页 Landing Page

- **目标**：5 秒说明是什么，30 秒展示为什么值得采用。
- **模块**：Hero、核心能力、架构流程、测试证据、CTA、GitHub Star/Fork/Issue。
- **CTA**：立即运行、查看架构、查看安全能力、访问 GitHub。
- **验收**：桌面/移动端首屏可读；主要 CTA 不超过 3 个；无虚假指标。

## WEB-02：能力与架构页

- 展示 chief、contract、scheduler、review loop、integration、cost/resilience/HITL 等模块。
- 使用 SVG 架构图和逐步动画，动画必须支持 reduced-motion。
- 每个模块链接到对应 `docs/` 卡片和源代码。
- 验收：所有链接有效；图中名称与代码目录一致；无复制粘贴后失真。

## WEB-03：安全增强页

- 展示 DeepSec-inspired 但独立实现的安全闭环：扫描、策略、HITL、修复、回归。
- 明确 DeepSec 参考来源、许可证审查和“不复制源码”的边界（与 `docs/deepsec-security-extension.md` §10 一致）。
- 展示一份本地 fixture 的脱敏安全报告样例，**标明 SARIF/JSON 格式**与 CLI 退出码契约（0=allow / 2=block / 3=error）。
- 验收：风险分级、证据、阻断条件、未覆盖范围均有说明；未落地能力标 planned，不提前宣称。

## WEB-04：交互式 Demo 页

- MVP 使用预生成 fixture 和事件回放，模拟架构生成、专家并行、扫描发现和发布门禁。
- 后续可增加受限后端任务，但必须 tenant/API Key/预算/超时/沙箱齐全。
- 不允许用户输入直接拼接 shell 命令；不允许默认访问互联网。
- 验收：Demo 可重复、无真实密钥、无外部副作用、错误状态可展示。

## WEB-05：文档中心

- 导航：Quick Start、架构、工作卡片、API、配置、安全、部署、FAQ。
- 版本与仓库 tag 对齐；页面显示文档版本和更新时间。
- 支持站内搜索，优先静态索引。
- 验收：关键文档 2 层内可达；代码示例可复制；命令与 CI 真实可运行。

## WEB-06：GitHub 社区页

- 强关联仓库：GitHub 源码、Releases、Issues、Discussions、Security Policy、Contributing。
- 展示 README badge、release、测试状态、许可证、贡献入口。
- 动态 GitHub API 做缓存、失败降级和匿名访问；不要让页面依赖单个 API 请求才能渲染。
- 验收：GitHub 不可用时页面仍可浏览；外链安全使用 `rel="noopener noreferrer"`。

## WEB-07：安全与透明度页

- 展示威胁模型、信任边界、默认禁用 shell、动态检查开关、数据保留、脱敏、漏洞披露流程。
- 提供 `SECURITY.md`、CHANGELOG、审计证据和已知限制入口。
- 验收：不会泄露内部路径、token、租户数据和真实扫描目标。

## WEB-08：推广内容页

- 内容类型：技术文章、版本发布、案例、性能/成本报告、贡献者故事。
- 每篇内容包含日期、版本、事实来源、代码/测试证据和免责声明。
- 支持 Open Graph、Twitter Card、JSON-LD、canonical URL。
- 验收：分享预览正确；无 SEO 关键词堆砌；内容可回溯到 commit/release。

---

## 4. GitHub 集成细节

### 必备入口

```text
/                  首页
/docs              文档
/security          安全能力与边界
/demo              可回放演示
/github            仓库与社区
/changelog         版本记录
```

### GitHub 数据模型

```python
@dataclass
class GitHubProjectSnapshot:
    repository_url: str
    stars: int | None
    forks: int | None
    open_issues: int | None
    latest_release: str | None
    default_branch: str | None
    fetched_at: float
    source: str = "github_api_or_static"
```

### 集成规则

1. 仓库 URL 由配置提供，不在组件内散落硬编码。
2. GitHub API 请求设置超时、缓存和 rate-limit 退避。
3. API 失败时显示静态仓库信息，不阻断首屏。
4. webhook/CI 更新 release 和 changelog 时做签名校验。
5. Issues/Discussions 只做链接，不在官网复制用户私密内容。
6. GitHub token 只存在 CI secret 或服务端 secret store，绝不进入前端 bundle。

---

## 5. 工程工作流卡片

## WEB-09：站点契约与内容事实源

- 依赖：DeepSec 安全方案 SEC-01
- 定义页面路由、内容 frontmatter、版本字段、GitHub 配置和安全声明模板。
- 验收：页面内容可由 Markdown 构建；链接检查和 frontmatter 校验通过。

## WEB-10：前端实现与设计系统

- 依赖：WEB-09
- 建立颜色、间距、字体、代码块、风险等级、状态 badge 设计 token。
- 采用“技术可信、克制、可读”的 B2B 工程产品视觉，不做过度动画。
- 验收：响应式、键盘导航、focus 状态、WCAG AA 对比度、reduced-motion。

## WEB-11：GitHub 数据适配器

- 依赖：WEB-09
- 实现静态配置、API adapter、缓存、失败降级、rate-limit 处理。
- 验收：mock API 成功/超时/403/500；页面可离线构建。

## WEB-12：安全 Demo 与事件回放

- 依赖：SEC-02、SEC-03、SEC-09、SEC-11（ScopeManifest）、WEB-10
- 只提供预生成安全扫描事件；事件与 StreamEvent schema 对齐；报告使用脱敏 SARIF/JSON 样例。
- Demo 展示动态验证的 ScopeManifest 授权闸门（白名单外/私网目标被拒绝的样例回放），不演示真实攻击。
- 验收：访客不能触发任意命令；demo 结果可重复；敏感信息扫描通过。

## WEB-13：CI/CD 与质量门禁

- 依赖：WEB-10、WEB-11
- CI 步骤：格式化、类型检查、单测、构建、链接检查、依赖漏洞检查、静态资源大小检查。
- 发布只从受保护分支和 tag 触发；preview 与 production 环境分离。
- 验收：构建失败不发布；source map 策略明确；依赖 lockfile 提交。

## WEB-14：可观测、隐私与合规

- 依赖：WEB-11、现有 data_compliance
- 默认不收集个人身份数据；如需分析只使用匿名、可关闭的方案。
- CSP、HSTS、X-Content-Type-Options、Referrer-Policy、Permissions-Policy。
- 验收：安全头检查通过；无第三方追踪器泄露；隐私页和 cookie 声明完整。

## WEB-15：发布与推广

- 依赖：WEB-13、WEB-14
- 发布节奏：首个 MVP、首个安全增强 preview、稳定版、案例版。
- 推广素材：README 首屏、30 秒 GIF、架构图、威胁模型图、测试证据、博客。
- 渠道：GitHub Release、Discussions、技术社区、团队内部技术分享；避免夸大安全能力。
- 验收：每个宣传结论有代码/测试/文档证据；版本号和仓库 tag 一致。

---

## 6. 官网验收标准

- [ ] 首页 5 秒内说明项目定位与主要价值。
- [ ] 所有核心能力均链接到真实文档和源代码。
- [ ] GitHub 仓库、release、issue、security policy 入口可用。
- [ ] GitHub API 不可用时页面仍可正常渲染。
- [ ] Demo 不执行访客任意输入、不暴露密钥、不访问真实目标。
- [ ] 移动端、键盘、屏幕阅读器和 reduced-motion 通过基本验收。
- [ ] CI 自动执行 build、typecheck、test、link check、security check。
- [ ] CSP 和安全响应头已配置。
- [ ] 统计默认关闭或匿名化，隐私说明清晰。
- [ ] 安全宣传以覆盖范围和证据为准，不做绝对安全承诺。

---

## 7. 未来展望

1. **交互式架构安全沙箱**：用户上传 fixture，隔离环境中生成架构、运行静态审计、导出报告。
2. **公开安全基线**：每个 release 发布规则版本、扫描范围、finding 数量、修复记录和限制。
3. **GitHub App**：以最小权限接入 PR，生成安全审计评论，但默认只读、不自动合并。
4. **可复现评测中心**：公开 benchmark、成本、延迟、误报率、回归率，便于社区对比。
5. **企业私有部署**：官网展示部署拓扑、租户隔离、审计、数据留存和离线模型方案。
6. **贡献者生态**：安全规则、扫描适配器、Prompt 评测和文档均支持插件化贡献。
