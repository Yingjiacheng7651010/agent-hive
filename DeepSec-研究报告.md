# DeepSec 开源仓库研究报告

调研对象:https://github.com/Unclecheng-li/DeepSec(本地浅克隆于 `research-deepsec/`,main 分支,723 个文件,已逐项核对)

---

## 一、已核实事实(均以仓库实际文件为准)

### 1. 项目概况与架构

- **定位**:AI 安全攻防一体平台,由 VibeGuard 进化而来,统一 Shield(代码安全审计)+ Spear(授权渗透测试),面向"交付 AI 生成代码的开发者"。
- **多语言**:Python 3.10+ 核心(CLI/MCP/角色/工具系统)、TypeScript(VS Code 扩展 + Node LSP + tree-sitter SAST)、Rust(ratatui TUI + 原生 L1 LSP 预览)、Kotlin(JetBrains 插件)。
- **架构形态**:单一 Python 安全核心 + 三个客户端(CLI、Rust TUI、IDE 桥),共享统一 finding schema(`deepsec/core/finding.py`)与统一配置 `~/.deepsec/config.yaml`(代码实际读取的是 YAML;`DEEPSEC.md` 中 `config.toml` 为过期信息)。
- **运行产物**:`~/.deepsec/runs/`(LLM 用量元数据 + Spear 授权审计日志 `audit.log`)、`reports/`、`snapshots/`、`findings.db`。
- **内部模块**(已核对目录):cli / config / core / shield / spear / roles / tools / mcp / report / kb / plugins / traffic / i18n / target_state。

### 2. 许可证

- `LICENSE` 文件:**MIT**,版权行 `Copyright (c) 2026 VibeGuard contributors`(注意:README 底部写的是 "MIT © 2026 DeepSec contributors",两处归属不一致)。
- `pyproject.toml`:name=deepsec、version=0.2.0、license=MIT、作者 UncleC、分类器 "3 - Alpha"。
- 依赖:typer / rich / prompt_toolkit / httpx / openai / pydantic / pyyaml / toml / jinja2 / textual / beautifulsoup4 / lxml / pycryptodome / tree-sitter;可选:reportlab(PDF 报告)、mitmproxy+playwright(流量模块)。

### 3. Shield(防御侧,三层检测)

| 层 | 检测内容 | 速度 | 原理 |
|---|---|---|---|
| L1 | 幻觉包、硬编码密钥、不安全配置、AI 错误模式 | <50ms | 正则 + 熵分析 + 种子目录 |
| L2 | SQL 注入/XSS/SSRF/路径穿越/命令注入 | <2s | tree-sitter WASM AST |
| L3 | 缺失认证/限流/校验等语义漏洞 | <5s | LLM(DeepSeek/Claude/OpenAI/Ollama 等 13+ 家),默认关闭、opt-in |

- 子命令:`shield scan [--layer] [--format text|json|sarif|markdown|html] [--stream]`、`shield agent-audit`、`shield watch`、`shield supply-chain check [--private-package]`。
- 供应链安全模块:`dependency_confusion.py`、`typosquatting.py`;Agent 安全模块:`prompt_injection.py`、`data_exfil.py`、`tool_abuse.py`。
- **退出码语义**:存在活跃 high/critical 发现时退出码为 `2`(CI 应保留 SARIF)。
- 去重:`dedup.py` + IDE 设置 `dedupWithExistingTools`(与 SonarQube/Snyk/Semgrep/CodeQL 去重)。

### 4. Spear(攻击侧,授权渗透引擎)

- 由 MIT 版 VulnClaw 迁移而来,工作流 **Recon → Explore → Fact → Reflect → Report → PoC**;intel 模块含 attack / compliance / cve / findings / osint / remediation / topology。
- **授权门禁**:`scope.json` 的 `targets` 白名单为硬性闸门(不在列表内一律拒绝);私网/回环/链路本地/组播/保留地址即使列入白名单也拒绝;默认阻止 RFC1918 网段。
- **签名**:HMAC-SHA256 签名机制存在,但 README 明确说明已放宽为可选(`signature`/`signer` 字段保留但忽略,授权只校验 targets + 可选时间窗口);`spear-guide.md` 仍描述强签名流程 —— 文档间有出入。
- **审计日志**:每次 run/recon 前写 `~/.deepsec/runs/<id>/audit.log`,记录 target / command / timestamp / signer / scope 文件 / authorization hash。
- 角色 5 个 YAML:`pentester / redteam / auditor / blueteam / ctf_player`;工具 8 个 YAML:`nmap / dirsearch / subfinder / httpx / feroxbuster / ffuf / nuclei / sqlmap`。
- 报告:Markdown / SARIF / JSON / HTML + 攻击链 JSON;`deepsec/spear/report/` 含 `poc_builder.py`、`verifier.py`、`pdf_exporter.py`(注意:与 `deepsec/report/` 是两处目录,后者只有 attack_chain);`spear/intel/` 除 7 个核心模块外还有 `remediation_rules.py`、`tools.py`。
- Agent 引擎相当复杂:`agent_graph` / `loop_controller` / `reflexion` / `parallel_agents` / `team` / `anti_loop` / `constraint_policy` / `context_vault` / `correction_layer` 等 40+ 文件。

### 5. 技能包(Skill Packs)

- **技能定义共 57 个**:50 个目录式 SKILL.md(全部位于 `specialized/`,YAML frontmatter + Markdown 正文)+ 7 个扁平 `.md` 旧格式 core 技能(`core/`,loader 兼容加载)。
- 格式:YAML frontmatter(name/description)+ Markdown 正文,统一结构 **Domain / Boundaries / Pivot Hints / Exit Evidence**;支持 `references/` 引用目录。
- `loader.py` 支持目录格式(`<name>/SKILL.md` + references)与旧扁平 `.md` 格式;`resolver` / `routing` / `dispatcher` / `flag_skills` 负责装载与路由。
- specialized 覆盖 OWASP 全谱系 `redteam-*-detail-pack`(sqli/xss/ssrf/ssti/xxe/cmdi/csrf/deserialize/open-redirect/subdomain-takeover/clickjacking/cache-poison/evasion/postex/ad/api/auth/cloud/container/crypto/file/injection/logic/mobile/network/payload/recon/reverse/web 等),另有 ctf-web/crypto/misc、osint-recon、cve-triage、hackerone、android-pentest、ai-mcp-security 等。
- 工具 YAML 通过 `skills: [web/verification]` 命名空间绑定技能;角色定义允许的工具集、skill 命名空间、模型偏好与执行预算。
- `warstories/`:攻击链复盘 Markdown(如 PHP 反序列化案例)。

### 6. CLI 与 API 集成点

- **CLI 全貌**(核对 `deepsec/cli/app.py`):根命令 `report / tui / chat / tools / restore`;子命令组 `shield`(scan/agent-audit/watch/supply-chain check)、`spear`(run/recon/roles/tools)、`snapshot`(create/list)、`config`(init/set/show)、`scope`(sign/verify)。入口 `deepsec = deepsec.cli.app:app`。
- **机器可读输出**:`--format json|sarif --output -`、`--stream`(NDJSON 事件流,供 TUI 与 dsh 插件消费)。
- **dsh 插件**(`dsh-plugins/`,与 DeepSeek Harness 生态直接对接,本地核对):
  - `dsh-deepsec-shield`:工具 `deepsec_scan / deepsec_agent_audit / deepsec_supply_chain / deepsec_report`;
  - `dsh-deepsec-spear`:工具 `deepsec_scope_sign / deepsec_scope_verify / deepsec_spear_recon / deepsec_spear_run / deepsec_spear_catalog`;
  - 薄封装:子进程调用 `deepsec` CLI 采集 JSON,授权/审计全在 Python 侧;符合 dsh 插件规范(name/inject/Config/apply),`dsh plugin add <path>` 安装;含授权门禁负向冒烟测试 `smoke.mjs`。
- **GitHub Action**(`action.yml`,composite):仍为 **VibeGuard 品牌**,运行 **Node `dist/cli.js`(TypeScript 扫描器,非 Python 核心)**;支持 fail_on、SARIF、GitHub annotations、PR 评论/内联 review、HTML findings dashboard、SOC2/ISO27001 合规报告、SQLite findings 库、私有 dashboard ingest 端点。
- **MCP**:实际代码是 **MCP 客户端**生命周期管理器(stdio/SSE/HTTP attach、registry、router、diagnostics),`MCPRouter` 把中英文自然语言意图映射到外部 MCP server 工具(`chrome-devtools` / `burp` / `fetch` / `memory`)。**README 声称的"内置 MCPServer 可被 Claude Desktop 调用"在代码中未找到对应类 —— 文档漂移**。
- **IDE**:VS Code 扩展 + Node LSP,`deepsecBridge.ts` 调 Python CLI(`json --output -`)并降级回 TS 实现;JetBrains 插件(Kotlin,`gradlew buildPlugin`)复用 LSP;Rust 原生 L1 LSP 预览(`rust-lsp/`)。
- **其他**:Dockerfile + docker-compose;CI(`ci.yml`)含 node / python / tui / jetbrains-plugin / docker 五个 job;内部插件框架 `deepsec/plugins/`(base/registry/runtime/integration + web 插件 headers/js_endpoints/jwt);流量模块 `deepsec/traffic/`(mitmproxy+playwright 可选,capture/normalize/replay/scope)。

---

## 二、推断的设计意图

1. **"抓出 AI 漏掉的"**——产品重心在 AI 生成代码的审计:幻觉包/依赖混淆/typosquatting、AI 错误模式、Agent 配置审计(prompt injection、数据外泄、工具滥用);`ai-code-scan` 模式用 git blame 归因只报 AI 相关行。
2. **Python-first 重构战略**:把 TS/VibeGuard 扫描器与 VulnClaw 引擎合并进单一 Python 核心,TS 侧退化为 IDE 桥。→ 集成时应优先走 Python CLI,而非 action.yml。
3. **"便利与强制分离"的门禁哲学**:IDE/TUI 层追求易用(签名从必选降为可选、TUI 直接管理白名单),但 Python 侧始终强制 targets 校验、私网拒绝与审计日志——门禁设计上不可被 UI 旁路。
4. **技能包= 受限自主 agent 的 prompt 工程化**:SKILL.md 不是攻击教程,而是"域判定 + 边界约束 + 转向提示 + 证据(artifact)要求(supported/verified 证据级别)",让 LLM 在限定域内自主测试并产出可验证证据,配合 warstories 复盘沉淀知识库(kb/retriever)。
5. **MCP 客户端化**:不自己做 MCP server,而是让 Spear agent 通过 MCP 挂接外部工具(Burp、Chrome DevTools、fetch、memory),扩展攻击面。
6. **生态互认**:自带 dsh 插件,显然是希望与 DeepSeek Harness 生态互通(当前基于 developer preview 契约)。

---

## 三、风险

1. **攻击性工具滥用风险**:Spear 是真实渗透引擎;白名单为使用者"自证"式维护,签名又已放宽为可选——没有外部签名源时门禁近乎形同虚设。落地自有环境必须叠加沙箱隔离与网络出口限制。
2. **文档漂移严重**:config.toml vs config.yaml;签名"可选" vs "强签名"两种描述并存;README 的"内置 MCP Server"与代码(实际为 MCP 客户端)不符;action.yml 仍是 VibeGuard 品牌并跑 TS 扫描器。集成前必须以代码为准,README 仅作参考。
3. **成熟度**:Alpha 阶段;README 声称"23 个 Python 测试"与本地 `tests/` 实际规模(78 个测试文件 = `tests/deepsec/` 9 个 + `tests/spear/` 及 intel/traffic 子目录 69 个,共约 849 个测试函数)严重不符;文档日期前移到 2026 年;个人项目,star/fork/活动度因 GitHub API 限流未能核实。
4. **隐私**:L3 会把源码发送给第三方 LLM,必须显式 opt-in;供应链检查依赖外部包索引。
5. **两套扫描器并存**:GitHub Action(Node/TS)与 Python CLI 行为可能不一致;依赖 nmap/sqlmap 等外部二进制,容器/CI 需自备。
6. **契约漂移**:dsh 插件基于 developer preview 契约,未来契约变动可能破坏兼容。

---

## 四、来源 URL

- 仓库主页(README 中文):https://github.com/Unclecheng-li/DeepSec
- README 原文:https://raw.githubusercontent.com/Unclecheng-li/DeepSec/main/README.md
- English README:https://github.com/Unclecheng-li/DeepSec/blob/main/README_EN.md
- 架构文档:https://github.com/Unclecheng-li/DeepSec/blob/main/docs/architecture.md
- Shield 指南:https://github.com/Unclecheng-li/DeepSec/blob/main/docs/shield-guide.md
- Spear 指南:https://github.com/Unclecheng-li/DeepSec/blob/main/docs/spear-guide.md
- 技能包开发文档:https://github.com/Unclecheng-li/DeepSec/blob/main/docs/skill-development.md
- DEEPSEC.md(迁移说明):https://github.com/Unclecheng-li/DeepSec/blob/main/DEEPSEC.md
- GitHub Action(action.yml):https://github.com/Unclecheng-li/DeepSec/blob/main/action.yml
- dsh 插件说明:https://github.com/Unclecheng-li/DeepSec/blob/main/dsh-plugins/README.md
- LICENSE:https://github.com/Unclecheng-li/DeepSec/blob/main/LICENSE
- Releases:https://github.com/Unclecheng-li/DeepSec/releases
- CI:https://github.com/Unclecheng-li/DeepSec/blob/main/.github/workflows/ci.yml
- 相关生态:https://github.com/PerryLink/dsh-skill-pack-security(另一 dsh 安全技能包,Apache-2.0)

> 本地证据:浅克隆位于 `research-deepsec/`(main,723 文件);README 另存于 `research-deepsec-readme.md`。GitHub REST API 因共享 IP 限流,未核实 star/fork/提交历史等元数据。
