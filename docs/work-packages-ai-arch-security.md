# AI 生成架构安全验证工作包（card-ai-arch-security）

> 批次状态：批次 1/2 实施中（threat_model✅、scope_auth✅、arch_security_llm✅、图/CLI 集成✅、规则引擎实施中）；批次 3（dist 扫描/golden 回归/文档）随后
> 依赖拓扑：批次 1（纯标准库）→ 批次 2（LLM + 图/CLI 集成）→ 批次 3（深化）；批次内无依赖包同批并行
> 角色说明：本卡片引入第五角色「安全」（ROLE_NAMES 扩展），契约改动见批次 2 的 security-role-contract

## 批次 1（P0：确定性核心，无 LLM、无网络）

### arch-threat-catalog
- 目标：建立可扩展的威胁模型库（STRIDE 六类 + AI 特有三类），作为规则引擎与 LLM 验证的共同分类框架。
- 接口契约：提供 `agent_hive.threat_model` 的 `ThreatCategory` / `Threat` / `ThreatCatalog` / `ValidationPolicy` / `load_threat_catalog()` / `apply_policy()`；全部纯标准库；`Threat.keywords` 为规则引擎匹配源。
- expected_output：`threat_model.py` + 内置目录说明（含每条威胁的资产/控制/整改建议）。
- depends_on：[]
- 验收标准：目录覆盖 STRIDE 六类 + AI 三类且每类 ≥1 条；`load_threat_catalog()` 可加载并校验完整性；`apply_policy` 对 critical/high/warning 阈值裁决正确；`fail_on_severity` 非法值（低于 high）被拒绝；排除项生效。
- 交付物：`workspace/arch-threat-catalog/`
- size：M；priority：1；轮次上限：3

### arch-security-rules
- 目标：实现 Shield 式确定性规则引擎，识别 AI 生成架构的幻觉引用、循环依赖、缺失安全控制、架构反模式。
- 接口契约：提供 `agent_hive.arch_security` 的 `SecurityFinding` / `SecurityReport` / 四个 `check_*` 检查器 / `merge_findings` / `validate_architecture`；输入为结构化 `architecture_object`（与 `contract_spec.ArchitecturePlan` 对齐）；循环依赖检查**复用 `scheduler.validate_dependency_graph`**（投影后调用，不重复实现）；引用字段只做字符串匹配、绝不 IO。
- expected_output：`arch_security.py` + 规则设计说明（每条检查的触发条件与证据格式）。
- depends_on：[arch-threat-catalog]
- 验收标准：幻觉引用（引用未定义模块/接口）被识别；A→B→A 循环依赖被标记；无认证/无输入校验/无密钥管理/无审计模块逐条产出 finding；risks 为空/无 owner/单点无失败处理被标记；`validate_architecture` 纯函数确定性（同输入同输出）；对无缺陷架构零误报。
- 交付物：`workspace/arch-security-rules/`
- size：L；priority：1；轮次上限：3

### arch-security-render
- 目标：确定性渲染 `SecurityReport` 为 markdown，供审批单、看板、最终报告共用。
- 接口契约：提供 `render_security_report_md(report) -> str`；输出含 verdict / 发现清单（模块、威胁 id、severity、证据、整改建议、source）/ 执行的检查清单；证据片段截断转义（防渲染注入，威胁 T-ENG-5）。
- expected_output：`arch_security.py` 中渲染函数 + 渲染样例文档。
- depends_on：[arch-security-rules]
- 验收标准：同输入同输出（确定性）；markdown 结构完整；恶意原文片段被转义不产生格式破坏；报告含可审计的检查清单。
- 交付物：`workspace/arch-security-render/`
- size：S；priority：1；轮次上限：3

### arch-security-rules-tests
- 目标：把批次 1 验收标准固化为可运行回归测试。
- 接口契约：仅通过公开模块接口测试；不 mock LLM（批次 2 的事）。
- expected_output：`tests/test_threat_model.py`、`tests/test_arch_security.py`、运行说明。
- depends_on：[arch-threat-catalog, arch-security-rules, arch-security-render]
- 验收标准：`uv run pytest tests/test_threat_model.py tests/test_arch_security.py` 可收集并运行；覆盖目录完整性、阈值裁决、四类规则检查、去重排序、确定性渲染；不启用新能力时既有回归不受影响。
- 交付物：`tests/` 对应文件
- size：M；priority：1；轮次上限：3

## 批次 2（P1：LLM 语义验证 + 管线集成）

### security-role-contract
- 目标：在契约单一事实源中新增「安全」角色，并重新生成 `skill/contracts.md`。
- 接口契约：`agent_hive/contract_spec.py` 的 `ROLE_NAMES` 增加 `"安全"`；新增 `ROLE_PROMPTS["安全"]`（deepsec 式语义扫描 + STRIDE 威胁建模 + 不可信数据处理 + 证据必引原文）与 `ROLE_SUMMARIES["安全"]`；最小权限与「评审」一致（只读 + 写报告，无 shell）。
- expected_output：`contract_spec.py` 改动 + 重新生成的 `skill/contracts.md` + 漂移说明。
- depends_on：[arch-threat-catalog, arch-security-rules]
- 验收标准：契约版本递增；`ROLE_NAMES` 含「安全」；`scripts/generate_contracts.py` 重新生成后 `--check` 通过；技能侧与程序侧共享同一角色事实源。
- 交付物：`workspace/security-role-contract/`
- size：M；priority：1；轮次上限：3

### llm-semantic-validator
- 目标：实现 deepsec 式 LLM 语义验证器（薄 seam），对结构化架构做威胁建模，输出结构化发现。
- 接口契约：提供 `agent_hive.arch_security_llm` 的 `LLMFinding` / `LLMSecurityFindings` / `LLM_SECURITY_AUDIT_PROMPT` / `run_llm_validation()`；结构化输出走 `_invoke_structured` 风格 + TRACKER 记账；异常/解析失败返回空列表；输入架构按不可信数据处理；`max_findings` 截断。
- expected_output：`arch_security_llm.py` + 提示词版本说明。
- depends_on：[security-role-contract, arch-security-rules]
- 验收标准：输出经 schema 校验；输入含恶意指令时发现不受操纵；LLM 失败不崩溃且规则引擎照常；发现带原文证据与整改建议；调用计入成本统计。
- 交付物：`workspace/llm-semantic-validator/`
- size：L；priority：1；轮次上限：3

### graph-security-integration
- 目标：把验证阶段插入管线（`plan_architecture → validate_architecture → approve_architecture`），实现 fail→回流闭环。
- 接口契约：`state.py` 新增 `architecture_object` / `security_report` / `security_report_object` / `security_verdict` / `security_policy` / `allow_insecure_architecture` / `skip_arch_security`；`graph.py` 新增节点与两条边；`approve_architecture` 审批单附带 `security_report`；`chief.plan_architecture` 同时产出 `architecture_object`；verdict=fail（未放行）时自动回流并把 remediation 汇总进驳回反馈；`chief.integrate`/`final_report` 呈现安全结论。
- expected_output：`state.py` / `graph.py` / `chief.py` 改动 + 集成说明。
- depends_on：[llm-semantic-validator, security-role-contract]
- 验收标准：图拓扑正确（验证先于审批①）；审批单含安全报告；fail 自动回流且反馈含整改建议；放行开关生效；skip 时行为与旧管线一致；断点续跑兼容；T1/T2 顾问模式不跑验证。
- 交付物：`workspace/graph-security-integration/`
- size：L；priority：1；轮次上限：3

### cli-security-policy
- 目标：新增 CLI 开关与策略文件加载（schema 校验、审计留痕）。
- 接口契约：`main.py` 新增 `--security-policy-file` / `--skip-arch-security` / `--allow-insecure-architecture`；策略 JSON 经 `ValidationPolicy` schema 校验，非法或放宽到低于 high 的 `fail_on_severity` 拒绝启动；跳过/放行写入审计记录。
- expected_output：`main.py` 改动 + `.env.example`/README 补充 + 策略样例 JSON。
- depends_on：[graph-security-integration]
- 验收标准：三个 flag 解析生效；非法策略文件拒绝启动；跳过与放行在审计/最终报告如实标注；默认不传任何 flag 时行为与旧管线一致。
- 交付物：`workspace/cli-security-policy/`
- size：M；priority：1；轮次上限：3

### security-llm-tests
- 目标：把批次 2 验收标准固化为回归测试（mock LLM，不真调模型）。
- 接口契约：mock `_invoke_structured` 与 TRACKER；通过公开接口与图 seam 验证。
- expected_output：`tests/test_arch_security_llm.py`、`tests/test_graph_arch_security.py`、`tests/test_cli_arch_security.py`、运行说明。
- depends_on：[llm-semantic-validator, graph-security-integration, cli-security-policy, arch-security-rules-tests]
- 验收标准：`uv run pytest` 全量可收集并运行；覆盖结构化解析、注入不可信数据、LLM 失败降级、图拓扑、审批单含报告、fail 回流、放行/跳过、断点续跑；既有回归不受影响。
- 交付物：`tests/` 对应文件
- size：L；priority：1；轮次上限：3

## 批次 3（P2：集成阶段验证 + 深化）

### dist-security-scan
- 目标：对集成后的 `dist` 交付树做静态安全扫描（secret/危险调用/敏感文件）。
- 接口契约：`arch_security.check_dist_artifacts(dist_dir, manifest, mask_patterns)`；复用 `data_compliance.DEFAULT_MASK_RULES` 的敏感模式；扫描结果并入 `IntegrationResult.checks` 语义或独立 `SecurityReport`。
- expected_output：`arch_security.py` 扩展 + 扫描样例。
- depends_on：[graph-security-integration, arch-security-rules]
- 验收标准：能识别硬编码密钥（复用脱敏模式）、`shell=True`/`eval`/`os.system` 等危险调用、`.env`/密钥文件落盘；对干净交付树零误报；默认只报告不阻断（显式策略可提升）。
- 交付物：`workspace/dist-security-scan/`
- size：M；priority：2；轮次上限：3

### threat-catalog-extensions
- 目标：支持外部威胁目录扩展包（企业/团队自有资产目录），并记录策略哈希到审计。
- 接口契约：`load_threat_catalog(extension_path=None)`；扩展目录与内置目录合并校验（id 冲突拒绝）；策略哈希进 `SecurityReport.policy_version`。
- expected_output：`threat_model.py` 扩展 + 扩展包样例 + 说明。
- depends_on：[arch-threat-catalog, cli-security-policy]
- 验收标准：扩展包可加载并合并；id 冲突被拒绝；策略哈希随报告可审计；无扩展时行为与批次 1 一致。
- 交付物：`workspace/threat-catalog-extensions/`
- size：S；priority：2；轮次上限：3

### security-golden-regression
- 目标：建立 golden 回归语料，防止提示词/规则改动引入漏报或误报。
- 接口契约：语料 = ≥10 个已知缺陷架构样例（每样例标注期望发现）+ 无缺陷样例；`scripts/verify.py` 增加安全回归步骤（或独立脚本）。
- expected_output：`tests/golden/` 语料 + 回归脚本 + 运行说明。
- depends_on：[llm-semantic-validator, arch-security-rules-tests, dist-security-scan]
- 验收标准：全部已知缺陷样例被检出；无缺陷样例零误报；提示词改动后一键回归；语料含注入型样例（威胁 T-ENG-1）。
- 交付物：`tests/golden/` + `scripts/verify.py` 扩展
- size：M；priority：2；轮次上限：3

### security-docs-board
- 目标：更新 README / SECURITY.md / 契约文档 / 项目看板，与实现保持一致。
- 接口契约：`SECURITY.md` 新增「架构安全验证」信任边界与开关说明；README 特性表与快速开始补充；看板登记本卡片各包状态。
- expected_output：文档更新 + 看板更新。
- depends_on：[graph-security-integration, cli-security-policy, dist-security-scan, threat-catalog-extensions, security-golden-regression]
- 验收标准：文档与实现一致；新开关、新角色、新威胁目录均有文档；`scripts/verify.py` 全绿（pytest + compileall + contract drift）。
- 交付物：README.md / SECURITY.md / skill/contracts.md（如涉及）/ 看板
- size：S；priority：2；轮次上限：3

---

## 集成与终验（首脑自理，depends_on 全部批次）

- 目标：合并各包交付物到共享根目录，跑关键路径端到端验证。
- 验收标准：`scripts/verify.py` 通过；端到端跑一次含安全验证的 `agent_hive run`（审批单含安全报告；故意注入缺陷架构可复现 fail→回流）；无孤立代码、无两份重复实现；最终报告如实呈现安全结论。
