# benchmarks —— 可复现 benchmark 报告框架

两个基准：**① 安全验证基准**（hive-security 规则引擎通道）与 **② 成本预算基准**（hive-cost CostGate）。
全部确定性：不使用 `random`，同输入两次运行输出逐字节一致。

## 环境

- Python >= 3.11；推荐 uv（`uv run` 自动同步 editable 安装：`hive-security` / `hive-cost`）。
- 零第三方依赖：两个 run.py 只依赖标准库 + 项目内包（`hive_security` / `hive_cost` / `scripts/security_benchmark.py`）。

## 命令

```bash
# ① 安全验证基准：调 scripts/security_benchmark.py（llm_enabled=False，纯规则引擎）
uv run python benchmarks/security/run.py

# ② 成本预算基准：三档预算（宽松/中等 70%/严格 50%）跑 CostGate
uv run python benchmarks/cost/run.py
```

每次运行产出：

| 基准 | 确定性产物 | 环境相关 sidecar（不进逐字节对比） |
|---|---|---|
| security | `benchmarks/security/results.json` + `report.md`（模板渲染） | `results.meta.json`（时间戳/延迟/Python 版本） |
| cost | `benchmarks/cost/results.json` + `report.md`（模板渲染） | `results.meta.json`（时间戳/Python 版本） |

## 版本（写入 results.json，随报告可审计）

- `hive-security` / `hive-cost` / `agent-hive`：运行期从 `importlib.metadata` 读取；
- 威胁目录版本：`hive_security.threat_model.THREAT_CATALOG_VERSION`（当前 1.0.0）；
- 契约版本：`agent_hive.contract_spec.CONTRACT_VERSION`（当前 1.3.0）。

## 如何重跑

```bash
# 直接重跑即覆盖（两次运行 results.json 逐字节一致）
uv run python benchmarks/security/run.py
uv run python benchmarks/security/run.py        # 与第一次逐字节一致
# 验证一致性（PowerShell）：
$h1 = (Get-FileHash benchmarks\security\results.json).Hash
uv run python benchmarks/security/run.py
$h2 = (Get-FileHash benchmarks\security\results.json).Hash
$h1 -eq $h2                                     # True
```

清空后重跑：删除 `benchmarks/*/results*.json` 与 `benchmarks/*/report.md` 后重跑即可再生成。

## 确定性说明

- 轨迹生成（`benchmarks/cost/trace_generator.py`）：seed 固定为 `20250617`（仅文档用途），
  全部取值由**序号算术**派生（任务数/调用数/模型轮换/token/延迟），无 `random`；
- `results.json` **不含墙钟测量值**（安全基准的 avg/p99 延迟、时间戳）——这些是环境相关
  字段，落在 `results.meta.json` sidecar；因此两次运行 results.json 逐字节一致；
- 成本统计（均值/方差/降级/block/告警）全部来自确定性规则计算，与墙钟无关。

## 未覆盖范围（两个基准共同声明）

- 不对第三方产品（ASTRIDE / Agentic Radar / DeepSec 等）做未经授权实测；本框架不含任何
  第三方产品对比数据，所有数字只来自本仓库自己的规则引擎与 CostGate；
- 不虚构数字：所有输出字段均由真实运行产生，模板占位符渲染前必须全部有值（渲染器检测残留并报错）；
- 安全基准只测规则引擎通道（`llm_enabled=False`），不纳入 LLM 语义验证通道；
- 成本基准使用内置静态价格表（`MODEL_PRICING`），不接入真实 LLM 计费 API；
- 延迟为单机测量值，跨机器不可比；检出率/误报率与语料分布强相关（语料见 `tests/golden/`）。
