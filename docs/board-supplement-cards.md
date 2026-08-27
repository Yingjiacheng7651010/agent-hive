# 项目看板：补充工作卡片 —— 生产级 agent 能力底座

> 背景：基于 `agent-hive-审计与研发建议.md` 的补充分析，从字节跳动 agent 开发工程师视角识别出的 9 个生产级能力缺口。
> 核心策略：保留"编排大脑"（chief + contract + review loop + 安全围栏），重做"能力手脚"（worker 层、基础设施层）。

---

## 看板总览

| 卡片 | 优先级 | 类型 | 依赖 | 状态 | 位置 |
|------|--------|------|------|------|------|
| card-cost-control | **P0** | 工程/成本 | - | ✅ 已完成 | `agent_hive/cost_control.py` |
| card-model-resilience | P0.5 | 可靠性 | - | ✅ 已完成 | `agent_hive/model_resilience.py` |
| card-async-hitl | P0.5 | 工程 | - | ✅ 已完成 | `agent_hive/async_hitl.py` |
| card-tool-registry | P1 | 架构 | - | ✅ 已完成 | `agent_hive/tool_registry.py` |
| card-streaming | P1 | 体验 | - | ✅ 已完成 | `agent_hive/streaming.py` |
| card-prompt-management | P1.5 | 工程 | card-tool-registry（可选） | ✅ 已完成 | `agent_hive/prompt_management.py` |
| card-multi-tenancy | P2 | 架构/安全 | card-distributed-engine（可选） | ✅ 已完成 | `agent_hive/multi_tenancy.py` |
| card-distributed-engine | P2 | 架构 | card-cost-control, card-model-resilience（建议先） | ✅ 已完成 | `agent_hive/distributed_engine.py` |
| card-data-compliance | P2 | 合规 | card-multi-tenancy（建议先） | ✅ 已完成 | `agent_hive/data_compliance.py` |
| **card-ai-arch-security** | **P0/P1/P2（分批）** | 安全 | SEC 批次拓扑（见文档 §9） | 🚧 实施中（批次1✅威胁目录/规则引擎进行中；批次2 图集成✅/CLI✅/LLM seam✅） | `docs/card-ai-arch-security.md` + `docs/work-packages-ai-arch-security.md` |
| **deepsec-security-extension** | **P0-P1.5** | 安全 | 现有 integration/async-hitel/multi-tenancy | 🚧 核心已落地（ScopeAuthorizer✅/SARIF 进行中/退出码契约） | `docs/deepsec-security-extension.md` |
| **card-website** | P1 | 产品/推广 | W1 骨架无硬依赖；安全页依赖 SEC 落地 | 📋 设计已落盘（含评审修正），待审批 | `docs/card-website.md` + `docs/website-promotion-workflow.md` |
| **DeepSec 研究报告** | 调研 | 事实核查 | - | ✅ 已完成（本地浅克隆 723 文件逐项核对） | `DeepSec-研究报告.md` |

---

## 安全增强与官网推广扩展（待审批批次）

> 调研结论：`github.com/Unclecheng-li/DeepSec` 为 MIT 许可的 AI 安全攻防平台（Alpha 0.2.0）。仅借鉴其 Shield 分层审计、Spear 授权门禁与机器可读输出思想，**不复制其源码**；Spear 攻击引擎与 Node/TS GitHub Action 路径明确不采用。
> 三份方案文档的依赖已对齐：SEC 安全扩展（`docs/deepsec-security-extension.md`，含 ScopeManifest/SARIF/Python-first 适配器契约）→ 架构安全卡（`docs/card-ai-arch-security.md`，插入审批关口一之前）→ 官网（`docs/card-website.md`，安全页二期与 SEC 批次联动）。

---

## 优先级与批次规划

### 批次 1：生存底线（P0 - P0.5）

> 目标：让 agent 框架能在生产环境安全运行，不崩溃、不跑飞、不卡死。

| 卡片 | 预计工作量 | 并行度 | 说明 |
|------|-----------|--------|------|
| **card-cost-control** | 2-3 周 | ✅ 可并行 | 无外部依赖，可独立启动 |
| **card-model-resilience** | 1-2 周 | ✅ 可并行 | 无外部依赖，可独立启动 |
| **card-async-hitl** | 2-3 周 | ✅ 可并行 | 无外部依赖，可独立启动 |

**批次 1 预计总工期**：2-3 周（三张卡可并行）

### 批次 2：能力扩展（P1 - P1.5）

> 目标：让 agent 具备可扩展的工具生态、可见的执行过程、可优化的 prompt 体系。

| 卡片 | 预计工作量 | 并行度 | 说明 |
|------|-----------|--------|------|
| **card-tool-registry** | 2-3 周 | ✅ 可并行 | 无外部依赖 |
| **card-streaming** | 1-2 周 | ✅ 可并行 | 无外部依赖 |
| **card-prompt-management** | 2-3 周 | ✅ 可并行 | 依赖 card-tool-registry（可选，可先做核心） |

**批次 2 预计总工期**：2-3 周（三张卡可并行）

### 批次 3：规模与合规（P2）

> 目标：支持多租户、分布式部署、数据合规，让框架可服务企业级用户。

| 卡片 | 预计工作量 | 并行度 | 说明 |
|------|-----------|--------|------|
| **card-distributed-engine** | 4-5 周 | ⚠️ 建议做完批次 1 | 依赖成本控制和容错机制 |
| **card-multi-tenancy** | 2-3 周 | ✅ 可先行做路径隔离 | 核心隔离机制可独立实现 |
| **card-data-compliance** | 2-3 周 | ✅ 可并行 | 脱敏和审核机制独立 |

**批次 3 预计总工期**：4-5 周（分布式引擎是瓶颈路径）

---

## 依赖关系图

```
批次 1（P0-P0.5）          批次 2（P1-P1.5）          批次 3（P2）
┌────────────────┐        ┌────────────────┐        ┌────────────────┐
│ card-cost-     │        │ card-tool-     │        │ card-          │
│ control        │───────▶│ registry       │───┐    │ distributed-   │
└────────────────┘        └────────────────┘   │    │ engine         │
                                                │    └────────────────┘
┌────────────────┐        ┌────────────────┐   │          │
│ card-model-    │────────│ card-streaming  │   │          │
│ resilience     │        └────────────────┘   │          │
└────────────────┘                              │          │
                                                │          ▼
┌────────────────┐        ┌────────────────┐   │    ┌────────────────┐
│ card-async-    │        │ card-prompt-   │   │    │ card-multi-    │
│ hitl           │        │ management     │───┘    │ tenancy        │
└────────────────┘        └────────────────┘        └────────────────┘
                                                           │
                                                           ▼
                                                     ┌────────────────┐
                                                     │ card-data-     │
                                                     │ compliance     │
                                                     └────────────────┘
```

---

## 执行顺序建议

### 推荐路径（最短 dependency chain）

```
Week 1-3: 批次 1 三张卡并行
  ├── card-cost-control: 先做 TokenEstimator + CostTracker 核心
  ├── card-model-resilience: 先做 RetryStrategy + 简单 fallback
  └── card-async-hitl: 先做 ApprovalQueue 内存实现 + sync_ask 兼容层

Week 3-5: 批次 2 三张卡并行
  ├── card-tool-registry: 先做 ToolSpec + ToolRegistry 核心
  ├── card-streaming: 先做 StreamManager + StreamContext
  └── card-prompt-management: 先做 PromptRegistry + 模板引擎

Week 5-9: 批次 3 三张卡（注意依赖顺序）
  ├── card-distributed-engine: 4-5 周（瓶颈路径）
  ├── card-multi-tenancy: 先做路径隔离 + 配额检查（2 周）
  └── card-data-compliance: 先做脱敏器 + 审计日志（2 周，可等多租户完成后做租户级）
```

---

## 终验标准

所有卡片完成后，运行以下验证：

- [ ] `uv run python scripts/verify.py`：通过（pytest + compileall + contract drift）
- [ ] 成本控制：每个 run 有预算上限，超限自动降级，成本数据可审计
- [ ] 模型容错：连续 5 次 API 失败后自动切 fallback，不崩溃
- [ ] 异步 HITL：审批请求进队列，超时自动决策，可通过 API 审批
- [ ] 工具注册表：新增工具不需改 specialists.py，注册即可用
- [ ] 流式输出：agent 思考过程实时可见，SSE 格式可消费
- [ ] Prompt 管理：prompt 版本化、可 diff、A/B 测试可配置
- [ ] 多租户：不同租户数据隔离，配额独立，认证生效
- [ ] 分布式引擎：多 worker 并发执行，单 worker 崩溃不影响其他
- [ ] 数据合规：敏感数据脱敏，数据按策略清理，审计日志完整