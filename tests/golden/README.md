# Golden 回归语料说明（card-ai-arch-security 批次 3）

本目录的 JSON 样例是架构安全验证规则引擎的回归基线，由 `scripts/security_golden.py` 驱动，
并已接入 `scripts/verify.py`。运行：`uv run python scripts/security_golden.py`。

## 样例格式

```json
{
  "name": "样例名",
  "architecture": { "overview": "...", "modules": [...], "risks": [...] },
  "expect_verdict": "fail",
  "must_hit": ["T-HALL-1"],
  "must_not_hit": []
}
```

- `must_hit`：确定性规则引擎**必须**产出的 threat_id（漏报即失败）。
- `must_not_hit`：**不得**产出的 threat_id（误报即失败）。
- 干净样例（expect_verdict=pass）必须零 finding。

## 覆盖范围（14 样例）

| 类别 | 样例 |
|---|---|
| 幻觉引用 | 幻觉引用未定义模块、提示注入不可操纵规则引擎（dogfooding） |
| 结构反模式 | 循环依赖、risks 空缺、模块无 owner |
| 缺失安全控制 | 认证、审计溯源、工具白名单、密钥、隐私合规、越权 |
| 执行守卫 | 执行接口无守卫与降级（T-SAFE-1） |
| 零误报 | 干净架构一、干净架构二 |

## 已知语义边界（引擎按契约行事，非缺陷）

1. 规则引擎只消费结构化 `architecture_object`，不解析 markdown。
2. 缺失控制检查的触发条件是「模块文本命中威胁 keywords 且缺失控制词」。真实目录中
   部分威胁的 keywords 与控制词重叠（如 T-DOS-1 的限流/配额/预算/重试/超时全部出现在
   control 文本中），导致这类威胁在缺失控制通道上「命中即已设计」，不会产出 finding；
   其检出依赖 LLM 语义验证通道或未来目录措辞调整。
3. T-TAMP-1（注入类）与 T-SPOOF-2（多租户）同理存在 keywords 与控制词重叠，
   规则通道产出有限；LLM 通道不受影响（`llm_verdict_requires_rule` 控制其裁决权重）。
4. `check_dependency_cycle` 产出的 T-PATT-1 severity 固定为 high（环是结构性问题），
   与目录中 T-PATT-1 的 medium 取值不同——目录值用于缺失控制/反模式检查。
