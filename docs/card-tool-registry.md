# 工作卡片：card-tool-registry —— 工具注册表与生命周期管理

> 优先级：P1 | 类型：架构 | 依赖：无
> 负责人：系统架构师 / 平台工程 | 轮次上限：3

---

## 1. 问题陈述

当前工具是 `@tool` 装饰器直接定义的函数，存在以下问题：
- 工具声明与实现耦合，没有独立的工具定义（tool spec）
- 没有工具注册表，无法按角色/权限动态分配工具
- 没有工具版本管理，改工具定义会影响所有使用它的 agent
- 没有工具调用监控（成功率、延迟、错误分布）
- 新增工具需要改代码，不支持热加载

## 2. 目标

建立工具注册表体系：工具定义（spec）→ 实现（impl）→ 注册（registry）→ 分配（assignment）→ 监控（monitoring），让工具成为一等公民，支持动态发现、版本管理、权限控制和调用监控。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/tool_registry.py

@dataclass
class ToolSpec:
    """工具定义（独立于实现的声明式规范）。"""
    name: str                                # 工具名称，如 "read_file"
    description: str                         # 工具描述（LLM 看到的）
    version: str                             # 语义版本号，如 "1.2.0"
    parameters: list["ToolParameter"]        # 参数定义
    returns: "ToolReturnType"                # 返回值定义
    categories: list[str] = field(default_factory=list)
    # 分类标签，如 ["file", "read", "core"]
    required_roles: list[str] = field(default_factory=list)
    # 允许使用的角色，空列表表示所有角色可用
    timeout_ms: int = 30000                  # 工具执行超时
    danger_level: Literal["safe", "caution", "dangerous"] = "safe"
    owner: str = ""                          # 工具维护者
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

@dataclass
class ToolParameter:
    name: str
    type: Literal["string", "integer", "boolean", "array", "object"]
    description: str
    required: bool = True
    default: Any = None

@dataclass
class ToolCallRecord:
    """一次工具调用的记录。"""
    tool_name: str
    tool_version: str
    arguments: dict
    result: str
    success: bool
    latency_ms: float
    error: str | None = None
    agent_role: str = ""
    timestamp: float = field(default_factory=time.time)
```

### 3.2 核心接口

```python
class ToolRegistry:
    """工具注册表：注册、发现、分配。"""

    def register(self, spec: ToolSpec, impl: Callable) -> bool:
        """注册工具。版本冲突时拒绝（需先 unregister）。"""

    def unregister(self, name: str, version: str | None = None) -> bool:
        """注销工具。version=None 时注销所有版本。"""

    def get(self, name: str, version: str | None = None) -> tuple[ToolSpec, Callable] | None:
        """获取指定版本的工具。version=None 返回最新版本。"""

    def list(self, filter_by: dict | None = None) -> list[ToolSpec]:
        """按条件查询工具列表。"""

    def get_for_role(self, role: str) -> list[tuple[ToolSpec, Callable]]:
        """获取指定角色可用的工具列表（自动过滤 required_roles）。"""


class ToolCallTracker:
    """工具调用追踪器：记录、聚合、告警。"""

    def record(self, record: ToolCallRecord):
        """记录一次工具调用。"""

    def stats(
        self,
        tool_name: str | None = None,
        since: float | None = None,
    ) -> dict:
        """查询工具调用统计：调用次数、成功率、平均延迟、p99 延迟。"""

    def top_failures(self, n: int = 10) -> list[ToolCallRecord]:
        """查询失败率最高的工具。"""
```

## 4. 实现方案

### 4.1 工具注册流程

```python
# 定义工具
spec = ToolSpec(
    name="read_file",
    version="1.0.0",
    description="读取工作区内任意文件",
    parameters=[
        ToolParameter(name="path", type="string", description="文件路径"),
    ],
    categories=["file", "read", "core"],
    required_roles=[],  # 所有角色可用
    danger_level="safe",
    owner="platform-team",
)

# 实现工具
def read_file_impl(path: str) -> str:
    # ... 实际实现 ...
    pass

# 注册
registry = ToolRegistry()
registry.register(spec, read_file_impl)

# 按角色分配
tools = registry.get_for_role("编码")
# 返回: [read_file, write_file, list_files, run_command]（按角色过滤后）
```

### 4.2 迁移方案

现有 `@tool` 装饰的函数逐步迁移到注册表模式：

```
阶段 1：注册表 + @tool 双轨运行（向后兼容）
阶段 2：新工具只走注册表，旧工具自动生成 ToolSpec
阶段 3：废弃 @tool 直接定义，统一走注册表
```

```python
# 兼容包装器：自动从 @tool 生成 ToolSpec
def tool_to_spec(tool_func) -> ToolSpec:
    """从 @tool 装饰的函数自动推断 ToolSpec。"""
    name = tool_func.name
    description = tool_func.description
    # 从函数签名推断参数...
    return ToolSpec(
        name=name, version="0.9.0", description=description,
        parameters=[...], categories=["legacy"],
    )
```

### 4.3 工具监控

```python
# 在工具调用链中自动记录
class MonitoredToolWrapper:
    """包装工具调用，自动记录指标。"""

    def __init__(self, spec: ToolSpec, impl: Callable, tracker: ToolCallTracker):
        self.spec = spec
        self.impl = impl
        self.tracker = tracker

    def __call__(self, **kwargs):
        start = time.time()
        try:
            result = self.impl(**kwargs)
            self.tracker.record(ToolCallRecord(
                tool_name=self.spec.name,
                tool_version=self.spec.version,
                arguments=kwargs,
                result=str(result)[:200],  # 截断，不存大量内容
                success=True,
                latency_ms=(time.time() - start) * 1000,
            ))
            return result
        except Exception as e:
            self.tracker.record(ToolCallRecord(
                tool_name=self.spec.name,
                tool_version=self.spec.version,
                arguments=kwargs,
                result="",
                success=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e),
            ))
            raise
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| 工具注册表核心 | `agent_hive/tool_registry.py` | ToolSpec/ToolRegistry/ToolCallTracker |
| 兼容包装器 | 同上 | `tool_to_spec()` 从现有 @tool 自动生成 ToolSpec |
| 监控集成 | 同上 | MonitoredToolWrapper 自动记录调用指标 |
| 现有工具迁移 | `agent_hive/specialists.py` | 将 4 个文件工具改为注册表模式 |
| 单元测试 | `tests/test_tool_registry.py` | 覆盖注册/发现/分配/监控全链路 |
| 迁移文档 | `docs/tool-migration-guide.md` | 从旧 @tool 迁移到注册表的指南 |

## 6. 验收标准

- [ ] 工具可注册、可注销、可按版本查询
- [ ] 按角色分配工具时自动过滤 `required_roles`，编码/测试/评审/调研各有不同工具集
- [ ] 现有 4 个文件工具可通过兼容包装器无缝迁移，不破坏现有功能
- [ ] 工具调用记录自动写入结构化日志，包含耗时/成功/参数
- [ ] 工具调用统计可查询（调用次数、成功率、p99 延迟）
- [ ] 新增工具不需改 `specialists.py`，只需注册到 registry
- [ ] 注册表支持热加载（不重启进程即可注册新工具）

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-multi-tenancy | 配合 | 多租户场景下，工具注册表需按租户隔离 |
| card-distributed-engine | 配合 | 分布式引擎中工具注册表需跨节点同步 |
| card-data-compliance | 消费 | 工具调用记录是合规审计的重要数据源 |

## 8. 实现效果

**改造前**：新增工具需要改 `specialists.py` 的 `_make_file_tools()`，加 `@tool` 装饰器，重启进程。工具和角色绑定关系硬编码在 `if role in ("编码", "测试"):` 条件中。

**改造后**：新增工具只需注册到 ToolRegistry，指定 `required_roles` 即可。角色和工具的映射关系声明式配置，不再硬编码。工具调用有完整的监控数据，可回答"哪个工具失败率最高？""哪个角色调用了最多工具？"