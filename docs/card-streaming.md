# 工作卡片：card-streaming —— 流式输出

> 优先级：P1 | 类型：体验 | 依赖：无
> 负责人：全栈 / 后端工程 | 轮次上限：3

---

## 1. 问题陈述

当前架构是纯同步的：首脑调用 LLM → 等完整输出 → 专家调用 LLM → 等完整输出 → 评审调用 LLM → 等完整输出。用户看到的是"运行中...（30 秒后）→ 突然看到完整结果"。在字节内部，任何长时间运行的 agent 任务都必须支持流式输出——用户能看到 agent 正在做什么、思考什么，而不是等几十秒后突然看到结果。

## 2. 目标

建立端到端的流式输出机制：agent 的思考过程、工具调用、中间结果实时推送给用户，支持 SSE（Server-Sent Events）和 WebSocket 两种传输协议。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/streaming.py

@dataclass
class StreamEvent:
    """流式事件：agent 执行过程中的一个可观察时刻。"""
    type: Literal[
        "agent_start",       # agent 开始处理
        "agent_thought",     # agent 思考片段（文本流）
        "tool_call",         # agent 调用工具
        "tool_result",       # 工具返回结果
        "agent_end",         # agent 完成处理
        "phase_change",      # 阶段变更（如：架构→分包→派发）
        "error",             # 错误
        "progress",          # 进度（如 "3/5 包已完成"）
        "checkpoint",        # 检查点（可中断恢复的位置）
    ]
    timestamp: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)
    run_id: str = ""
    agent_id: str = ""

@dataclass
class StreamSession:
    """一个流式会话：连接多个 StreamEvent 到同一个消费者。"""
    session_id: str
    created_at: float = field(default_factory=time.time)
    closed: bool = False
```

### 3.2 核心接口

```python
class StreamManager:
    """流式管理器：生产事件、消费事件、管理会话。"""

    def create_session(self) -> str:
        """创建新的流式会话，返回 session_id。"""

    def close_session(self, session_id: str):
        """关闭会话。"""

    def publish(self, session_id: str, event: StreamEvent):
        """向会话发布事件。线程安全。"""

    def subscribe(
        self, session_id: str,
        event_types: list[str] | None = None,
    ) -> Generator[StreamEvent, None, None]:
        """订阅会话的事件流。可指定事件类型过滤。"""

    def subscribe_sse(
        self, session_id: str,
    ) -> Generator[str, None, None]:
        """订阅并返回 SSE 格式的文本流（用于 HTTP 接口）。"""


class StreamContext:
    """上下文管理器：在 agent 执行期间自动发布事件。"""

    def __init__(self, session_id: str, manager: StreamManager):
        self.session_id = session_id
        self.manager = manager

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.manager.publish(self.session_id, StreamEvent(
            type="agent_end", data={"reason": "completed"},
        ))

    def thought(self, text: str):
        """发布思考片段。"""
        self.manager.publish(self.session_id, StreamEvent(
            type="agent_thought", data={"text": text},
        ))

    def tool_call(self, tool_name: str, arguments: dict):
        """发布工具调用事件。"""
        self.manager.publish(self.session_id, StreamEvent(
            type="tool_call", data={"tool": tool_name, "arguments": arguments},
        ))

    def tool_result(self, tool_name: str, result: str):
        """发布工具返回事件。"""
        self.manager.publish(self.session_id, StreamEvent(
            type="tool_result", data={"tool": tool_name, "result": result[:500]},
        ))

    def progress(self, current: int, total: int, message: str = ""):
        """发布进度事件。"""
        self.manager.publish(self.session_id, StreamEvent(
            type="progress",
            data={"current": current, "total": total, "message": message},
        ))

    def phase(self, phase: str):
        """发布阶段变更事件。"""
        self.manager.publish(self.session_id, StreamEvent(
            type="phase_change", data={"phase": phase},
        ))

    def error(self, error: str):
        """发布错误事件。"""
        self.manager.publish(self.session_id, StreamEvent(
            type="error", data={"error": error},
        ))
```

## 4. 实现方案

### 4.1 集成到现有流程

```python
# 在 graph.py 的节点函数中注入 StreamContext：

def specialist_node(state):
    stream_ctx = StreamContext(state["session_id"], stream_manager)
    with stream_ctx:
        stream_ctx.phase(f"专家执行：{pkg['role']}")
        stream_ctx.thought("开始分析工作包需求...")
        # ... 实际执行 ...
        stream_ctx.thought("分析完成，开始生成代码...")
        # ... 调用 LLM、工具 ...
        stream_ctx.tool_call("write_file", {"path": "..."})
        stream_ctx.tool_result("write_file", "已写入 xxx.py")
        stream_ctx.progress(1, 3, "编码完成")
        return result
```

### 4.2 SSE 传输格式

```
event: agent_thought
data: {"text": "开始分析工作包需求...", "timestamp": 1729412345.678}

event: tool_call
data: {"tool": "write_file", "arguments": {"path": "main.py"}, "timestamp": 1729412346.123}

event: progress
data: {"current": 1, "total": 3, "message": "编码完成", "timestamp": 1729412350.456}
```

### 4.3 存储抽象

```python
class StreamStore(ABC):
    """流式事件存储抽象，支持内存/文件/Redis 后端。"""

    @abstractmethod
    def append(self, session_id: str, event: StreamEvent): ...
    @abstractmethod
    def replay(self, session_id: str) -> list[StreamEvent]: ...
    @abstractmethod
    def list_sessions(self) -> list[str]: ...
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| 流式管理器 | `agent_hive/streaming.py` | StreamManager + StreamContext + StreamEvent |
| SSE 接口 | 同上 | `subscribe_sse()` 输出 SSE 格式 |
| 内存存储 | 同上 | StreamStore 的内存实现 |
| 单元测试 | `tests/test_streaming.py` | 覆盖事件发布/订阅/格式 |
| 集成测试 | `tests/test_streaming_integration.py` | 集成到真实 run 流程验证 |
| 看板集成 | 更新 `board.md` | 流式事件展示在看板 |

## 6. 验收标准

- [ ] agent 执行过程中，思考文本实时推送给订阅者（逐 chunk）
- [ ] 工具调用和返回结果可见（工具名 + 参数 + 截断结果）
- [ ] 阶段变更可见（"架构阶段"→"分包阶段"→"编码阶段"）
- [ ] 进度事件可见（"3/5 包已完成"）
- [ ] 错误事件可实时推送，不影响 agent 继续执行
- [ ] 多个消费者可同时订阅同一会话
- [ ] 事件可回放（replay），用于调试和审计
- [ ] 不开启流式时，行为与现有代码完全一致（向后兼容）
- [ ] 事件发布不影响 agent 执行性能（异步非阻塞）

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-distributed-engine | 配合 | 分布式引擎中流式事件需跨节点路由到正确的会话 |
| card-async-hitl | 数据源 | 流式事件可触发 HITL 审批请求（如"编码阶段完成，等待审批"） |
| card-data-compliance | 数据源 | 流式事件日志是审计记录的重要来源 |

## 8. 实现效果

**改造前**：用户看到黑屏等待 30 秒，然后突然看到完整结果。不知道 agent 在做什么、卡在哪里。

**改造后**：用户实时看到 agent 的思考过程——"正在分析需求..."、"正在调用 read_file 读取 architecture.md"、"正在生成代码..."、"已完成 3/5 个包"。用户体验从"黑盒等待"变为"透明可见"。也便于调试 agent 行为——回放流式事件即可看到完整的执行轨迹。