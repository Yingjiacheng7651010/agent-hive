# 工作卡片：card-async-hitl —— 异步人机协同

> 优先级：P0.5 | 类型：工程 | 依赖：card-distributed-engine（可选，可先独立实现）
> 负责人：后端工程 / 全栈 | 轮次上限：3

---

## 1. 问题陈述

当前 HITL（Human-in-the-Loop）使用 `input("批准？")` 同步阻塞，这意味着：
- 审批人不在线时整个 run 卡死
- 不支持审批超时 + 自动降级
- 不支持审批队列 + 优先级调度
- 不支持审批策略模板（"如果 X 条件满足，自动批准"）
- 无法集成到字节内部的审批平台（飞书审批/工作流）

## 2. 目标

将同步 HITL 改造为**异步审批队列**：审批请求进队列 → 审批人通过回调/Webhook 收到通知 → 审批结果异步返回 → 超时自动降级。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/async_hitl.py

@dataclass
class ApprovalRequest:
    """一次审批请求。"""
    id: str                              # 唯一标识，如 "approval_20261015_abc123"
    kind: Literal["architecture", "dispatch", "danger_confirm", "budget_exceed"]
    title: str                           # 审批标题，如 "审批架构方案"
    content: dict                        # 审批内容（结构化数据，非 markdown 文本）
    requester: str                       # 请求者（run_id / agent name）
    priority: int = 2                    # 1=紧急, 2=普通, 3=低优先级
    created_at: float = field(default_factory=time.time)
    timeout_ms: int = 300000             # 超时时间，默认 5 分钟
    auto_decision: dict | None = None    # 超时后的自动决策
    # 如 {"approved": True, "condition": "仅当变动文件 < 5 个"}
    callback_url: str | None = None      # 异步回调 URL（webhook）

@dataclass
class ApprovalResult:
    """审批结果。"""
    request_id: str
    approved: bool
    feedback: str = ""
    decided_by: Literal["human", "auto_timeout", "auto_policy"] = "human"
    decided_at: float = field(default_factory=time.time)
    decided_by_user: str | None = None   # 审批人身份（human 时）

@dataclass
class ApprovalPolicy:
    """审批策略模板：自动审批规则。"""
    name: str
    condition: str                       # 条件表达式，如 "len(files) < 5 and role == '编码'"
    auto_decision: dict                  # 条件满足时的自动决策
    priority: int = 1                    # 多个策略匹配时优先级高的生效
```

### 3.2 核心接口

```python
class ApprovalQueue:
    """异步审批队列。"""

    def submit(self, request: ApprovalRequest) -> str:
        """提交审批请求，返回 request_id。"""

    def poll(self, request_id: str, timeout_ms: int = 5000) -> ApprovalResult | None:
        """轮询审批结果（同步等待场景兼容）。"""

    def resolve(self, result: ApprovalResult) -> bool:
        """审批人提交审批结果。返回 False 表示 request_id 已超时/已处理。"""

    def pending_requests(self, filter_by: dict | None = None) -> list[ApprovalRequest]:
        """查看待审批列表（看板/API 用）。"""

    def stats(self) -> dict:
        """统计信息：待审批数、平均处理时长、超时率。"""


class ApprovalPolicyEngine:
    """审批策略引擎：自动审批规则匹配。"""

    def evaluate(self, request: ApprovalRequest) -> ApprovalResult | None:
        """检查是否有匹配的自动审批策略。"""

    def register_policy(self, policy: ApprovalPolicy):
        """注册一条审批策略。"""


# --- 存储抽象（支持多后端） ---

class ApprovalStore(ABC):
    """审批存储抽象，支持内存/文件/SQLite/Redis 后端。"""

    @abstractmethod
    def save_request(self, request: ApprovalRequest): ...
    @abstractmethod
    def save_result(self, result: ApprovalResult): ...
    @abstractmethod
    def get_request(self, request_id: str) -> ApprovalRequest | None: ...
    @abstractmethod
    def get_result(self, request_id: str) -> ApprovalResult | None: ...
    @abstractmethod
    def list_pending(self) -> list[ApprovalRequest]: ...
```

## 4. 实现方案

### 4.1 审批流程

```
agent run 触发审批点
    │
    ▼
ApprovalQueue.submit(request)
    │
    ├──▶ 策略引擎检查 ──▶ 匹配 → 自动决策（走 ApprovalResult，decided_by="auto_policy"）
    │
    └──▶ 不匹配 → 进入队列
              │
              ├──▶ 通知通道（可选）：飞书/邮件/Webhook
              │
              ├──▶ 等待审批人 resolve()
              │
              └──▶ 超时 → 自动决策（走 auto_decision，decided_by="auto_timeout"）
```

### 4.2 同步兼容层

为兼容现有 `Command(resume=_ask(...))` 模式，提供同步包装器：

```python
def sync_ask(interrupt_value: dict, auto_yes: bool, timeout_ms: int = 300000) -> dict:
    """兼容现有同步接口。内部调用异步队列 + poll。"""
    request = ApprovalRequest(
        id=f"approval_{uuid.hex()}",
        kind=interrupt_value.get("kind", "unknown"),
        title=interrupt_value.get("title", "审批请求"),
        content=interrupt_value,
        timeout_ms=timeout_ms,
        auto_decision={"approved": auto_yes},
    )
    queue.submit(request)
    # 等待审批结果（或超时自动决策）
    while True:
        result = queue.poll(request.id, timeout_ms=5000)
        if result is not None:
            return {"approved": result.approved, "feedback": result.feedback}
        # 检查超时
        if time.time() - request.created_at > request.timeout_ms / 1000:
            result = ApprovalResult(
                request_id=request.id, approved=auto_yes,
                feedback="审批超时，自动决策", decided_by="auto_timeout",
            )
            queue.resolve(result)
            return {"approved": auto_yes, "feedback": "审批超时，自动决策"}
```

### 4.3 审批 Webhook（可选，但推荐实现）

```python
# Flask/FastAPI 端点示例
@app.post("/api/v1/approvals/{request_id}/resolve")
def resolve_approval(request_id: str, body: dict):
    result = ApprovalResult(
        request_id=request_id,
        approved=body["approved"],
        feedback=body.get("feedback", ""),
        decided_by="human",
        decided_by_user=body.get("user", "unknown"),
    )
    queue.resolve(result)
    return {"status": "ok"}
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| 异步审批队列 | `agent_hive/async_hitl.py` | 核心实现（含策略引擎 + 存储抽象） |
| 内存存储实现 | 同上 | ApprovalStore 的内存后端（默认，零依赖） |
| SQLite 存储实现 | 同上 | ApprovalStore 的 SQLite 后端（持久化待审批项） |
| 同步兼容包装器 | 同上 | `sync_ask()` 兼容现有 `Command(resume=...)` |
| 单元测试 | `tests/test_async_hitl.py` | 覆盖提交/审批/超时/策略匹配全链路 |
| 看板集成 | 更新 `board.md` | 审批状态看板卡片 |
| 配置示例 | `.env.example` 补充 | `HIVE_APPROVAL_TIMEOUT_MS`、`HIVE_APPROVAL_STORE` |

## 6. 验收标准

- [ ] 提交审批请求后立即返回，不阻塞 agent run（agent run 在等待期间可做其他工作）
- [ ] 审批人通过 `resolve()` 接口提交结果后，agent 流程正确恢复
- [ ] 审批超时（默认 5 分钟）后自动走 `auto_decision`，不永久卡死
- [ ] 策略引擎支持自动审批规则，匹配时跳过人工审批
- [ ] 兼容现有 `Command(resume=...)` 同步接口（`sync_ask()` 包装器）
- [ ] 待审批列表可通过 `pending_requests()` 查询，支持看板展示
- [ ] 审批记录持久化（SQLite 后端），可审计
- [ ] 多个审批请求可并发在队列中，互不影响

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-cost-control | 消费者 | 预算超限警报可作为审批请求的触发条件 |
| card-distributed-engine | 数据源 | 分布式引擎中审批队列需共享（Redis 后端） |
| card-data-compliance | 配合 | 审批记录需要合规审计，存储策略需对齐 |

## 8. 实现效果

**改造前**：审批人在终端前输入 y/n，不在线则 run 卡死。无法集成到飞书审批流。

**改造后**：审批请求进入队列，审批人通过飞书/Web API 随时审批。支持超时自动决策，agent 流程不阻塞。支持审批策略模板（"架构方案变更 < 5 个文件自动批准"），减少人工介入频率。