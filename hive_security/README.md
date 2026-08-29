# hive-security

AI 架构安全验证独立零依赖包：**纯标准库**（dataclasses / json / re / argparse），
不依赖 pydantic / langchain。事实源与 `agent-hive` 的 `arch_security` / `threat_model`
同源：agent-hive 内部已改为薄壳引用本包。

## 30 秒上手

```bash
# 安装（零运行时依赖）
uv sync --extra dev          # 或 pip install -e .

# 扫描一份结构化架构 JSON
hive-security scan --input arch.json --format sarif --output report.sarif

# 只看 JSON 报告（默认输出到 stdout）
hive-security scan --input arch.json --format json

# 携带策略文件（可选）
hive-security scan --input arch.json --policy policy.json --format markdown
```

`arch.json` 形如：

```json
{
  "overview": "系统包含认证、鉴权与失败降级设计",
  "modules": [
    {"name": "auth", "responsibility": "提供统一认证、鉴权与身份管理", "interfaces": ["login()"], "owner_role": "编码"},
    {"name": "gateway", "responsibility": "请求路由", "interfaces": ["route()"], "owner_role": "编码", "depends_on": ["auth"]}
  ],
  "risks": ["网关故障时降级为只读"]
}
```

## 输出契约

- **用法**：`hive-security scan --input ARCH.json [--policy POLICY.json] [--format json|sarif|markdown] [--output PATH|-]`
- **格式**：`--format` 默认 `sarif`；`--output` 默认 `-`（stdout）。
  三种格式均**确定性**：同一输入逐字节同输出（无墙钟、无随机；`generated_at` 固定为纪元时间戳）。
- **退出码**：
  - `0` = 裁决 `pass` / `pass_with_warnings`
  - `2` = 裁决 `fail`（存在达到或超过 `fail_on_severity` 的发现，或警告超限）
  - `3` = 执行错误（文件缺失 / JSON 非法 / 策略非法 / 参数错误）
- **策略文件**（可选，白名单字段，缺省取默认值）：
  `fail_on_severity`（仅允许 `"critical"|"high"`）/ `max_warnings` /
  `llm_enabled` / `llm_verdict_requires_rule` / `exclusions` / `max_findings_per_threat`。
  白名单外字段或非法值一律拒绝（退出码 3）。

## 检查范围 / 未覆盖范围

**检查范围（确定性规则引擎，Shield 式）**：

- `check_hallucinated_references`：接口中「引用:/调用:/依赖:」前缀或反引号包裹的未定义名称（T-HALL-1，纯字符串模式匹配，绝不按引用值做 IO）
- `check_dependency_cycle`：模块依赖图循环（包内内置 `_validate_dependency_graph`：非空 / id 唯一 / depends_on 引用存在 / 三色 DFS 无环；仅环触发 T-PATT-1）
- `check_missing_security_controls`：命中威胁关键词但缺少对应控制设计（9 类威胁目录逐条匹配）
- `check_architectural_anti_patterns`：risks 空缺 / 模块无 owner_role / 模块数越界 / 有执行类接口却无失败处理设计（T-PATT-1 / T-SAFE-1）
- `check_dist_artifacts`：dist 交付树静态扫描（硬编码密钥 / `shell=True`、`os.system(`、`eval(`、`exec(` / `.env`、`*.pem`、`*.key`、`id_rsa`），复用包内 `_DEFAULT_MASK_PATTERNS`（base64 长串 / 密钥串 / 银行卡 / SSN / 邮箱）
- LLM 发现合并策略：`llm_verdict_requires_rule` 为真时，与规则发现无共识的 critical/high 降级为 medium

**未覆盖范围（明确不做）**：

- 不做 LLM 语义验证（`llm_enabled` 仅作策略字段透传；CLI 不调用任何模型）
- 不做 `scope_auth` / 动态代码执行 / 沙箱；引用字段只做模式匹配
- 不解析 markdown 架构（只消费结构化 JSON），避免解析漂移
- 不扫描超 1MB 或非 UTF-8 / 含 NUL 的文件（视为二进制跳过）
- 不承诺发现全部真实漏洞：规则引擎是确定性防线，需与人工评审 / 渗透测试互补

## 标准映射（CWE / OWASP Top 10 for LLM 2025）

`hive_security.cwe_map` 提供威胁目录 → 标准编号的静态映射；SARIF 输出中每个 result
的 `properties` 字段携带 `{"cwe": [...], "owasp_llm_top10": [...]}`（未知 threat_id
给空列表，不崩溃；映射为纯静态查表，不改变 SARIF 顶层结构）。

映射依据表（threat_id → 编号 → 依据一句话；CWE 依据 [cwe.mitre.org](https://cwe.mitre.org)，OWASP 依据 [genai.owasp.org](https://genai.owasp.org) 2025 版分类）：

| threat_id | CWE | CWE 依据 | OWASP LLM 2025 | OWASP 依据 |
|---|---|---|---|---|
| T-SPOOF-1 | CWE-287 | 认证/身份缺失 = Improper Authentication | — | 2025 分类无「认证」直接对应，不伪造 |
| T-SPOOF-2 | CWE-284 | 多租户隔离缺失 = Improper Access Control | — | 2025 分类无直接对应（LLM08 为向量/嵌入弱点，不符） |
| T-TAMP-1 | CWE-74 | 注入类（提示注入等）= Improper Neutralization ('Injection') | LLM01 | 提示注入 = Prompt Injection |
| T-TAMP-2 | CWE-78 | 命令执行无白名单 = OS Command Injection | — | 工具/命令执行安全属工程防护，2025 无直接对应 |
| T-REPU-1 | CWE-778 | 无审计日志 = Insufficient Logging | — | 2025 分类无「日志/审计」直接对应 |
| T-DISC-1 | CWE-798 | 密钥硬编码/泄露 = Use of Hard-coded Credentials | LLM02 | 机密泄露 = Sensitive Information Disclosure |
| T-DISC-2 | CWE-359 | 隐私/个人信息泄露 = Exposure of Private Personal Information | LLM02 | 个人信息泄露 = Sensitive Information Disclosure |
| T-DOS-1 | CWE-400 | 无限流/配额/预算耗尽 = Uncontrolled Resource Consumption | LLM10 | 无上限消耗 = Unbounded Consumption |
| T-ELEV-1 | CWE-269 | 越权/最小权限缺失 = Improper Privilege Management | LLM06 | 越权/过度授权 = Excessive Agency |
| T-SAFE-1 | CWE-693 | 无守卫/降级 = Protection Mechanism Failure | LLM05 | 输出未校验/降级缺失 = Improper Output Handling |
| T-PATT-1 | CWE-1047 | 循环依赖 = Modules with Circular Dependencies | — | 架构结构问题，2025 无直接对应 |
| T-HALL-1 | — | 幻觉无对应 CWE，如实空列表 | LLM09 | 幻觉/错误信息 = Misinformation |

> 修正说明：初稿中 T-SPOOF-1/T-SPOOF-2/T-ELEV-1/T-SAFE-1 曾映射 LLM08、T-DISC-1/T-DISC-2
> 曾映射 LLM06、T-DOS-1 曾映射 LLM04；按 2025 官方分类复核后修正（LLM08 = Vector and
> Embedding Weaknesses、LLM06 = Excessive Agency、LLM04 = Data and Model Poisoning，
> 语义均不符）。「不伪造编号」优先于「尽量映射」：无直接对应的威胁给空列表。

