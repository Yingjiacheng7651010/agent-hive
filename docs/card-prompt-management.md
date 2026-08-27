# 工作卡片：card-prompt-management —— Prompt 管理基础设施

> 优先级：P1.5 | 类型：工程 | 依赖：card-tool-registry（可选）
> 负责人：系统架构师 / AI 工程 | 轮次上限：3

---

## 1. 问题陈述

当前 prompt 管理存在以下问题：
- 角色提示词直接硬编码在 `prompts.py` 的 `ROLE_PROMPTS` 字典中
- 没有 prompt 版本管理——改 prompt 不可追溯，改完不知道效果变化
- 没有 prompt A/B 测试能力——无法对比不同 prompt 版本的效果差异
- 没有 prompt 性能监控——不知道哪个 prompt 的返工率高、哪个效果好
- 没有 prompt 模板化——角色提示词和工作包提示词混杂，难以复用

## 2. 目标

建立 prompt 管理的完整基础设施：版本化存储 → 模板引擎 → A/B 测试框架 → 效果监控。让 prompt 的优化迭代可追踪、可对比、可回滚。

## 3. 接口契约

### 3.1 核心数据结构

```python
# agent_hive/prompt_management.py

@dataclass
class PromptTemplate:
    """Prompt 模板：带版本管理的结构化提示词。"""
    name: str                            # 模板名称，如 "role.coder"
    version: str                         # 语义版本号，如 "2.1.0"
    template: str                        # Jinja2/Mustache 模板字符串
    variables: list[str]                 # 模板变量列表，如 ["goal", "architecture"]
    description: str                     # 用途说明
    tags: list[str] = field(default_factory=list)
    # 标签，如 ["role", "coder", "v2"]
    author: str = ""                     # 作者
    created_at: float = field(default_factory=time.time)
    parent_version: str | None = None    # 父版本（用于追踪 prompt 演化）
    hash: str = ""                       # 模板内容的 SHA256（自动计算）

@dataclass
class PromptVariant:
    """Prompt 变体：同一个模板的不同版本，用于 A/B 测试。"""
    template_name: str
    variant_name: str                    # 变体名称，如 "control", "variant_a"
    version: str                         # 引用的 PromptTemplate 版本
    weight: float = 1.0                  # A/B 流量权重，如 0.5 表示 50% 流量
    active: bool = True

@dataclass
class PromptEvalResult:
    """Prompt 效果评估结果。"""
    template_name: str
    variant_name: str
    version: str
    period: tuple[float, float]          # 评估周期
    total_calls: int = 0
    avg_attempts: float = 0.0            # 平均返工次数
    rework_rate: float = 0.0             # 返工率
    pass_rate: float = 0.0               # 一次通过率
    avg_tokens: float = 0.0              # 平均 token 消耗
    avg_latency_ms: float = 0.0          # 平均延迟
    total_cost_usd: float = 0.0
```

### 3.2 核心接口

```python
class PromptRegistry:
    """Prompt 注册表：版本化存储、检索、对比。"""

    def register(self, template: PromptTemplate) -> bool:
        """注册/更新 prompt 模板。hash 冲突时拒绝。"""

    def get(self, name: str, version: str | None = None) -> PromptTemplate | None:
        """获取指定版本的模板。version=None 返回最新版本。"""

    def list(self, name: str | None = None) -> list[PromptTemplate]:
        """列出所有模板（或指定名称的所有版本）。"""

    def diff(self, name: str, v1: str, v2: str) -> str:
        """对比两个版本的差异。"""

    def render(self, name: str, variables: dict, version: str | None = None) -> str:
        """渲染 prompt 模板（替换变量）。"""


class PromptABTest:
    """Prompt A/B 测试框架。"""

    def register_variant(self, variant: PromptVariant):
        """注册一个变体。"""

    def select_variant(self, template_name: str) -> PromptVariant:
        """按权重选择一个变体（随机）。"""

    def record_result(self, template_name: str, variant_name: str, result: dict):
        """记录一次执行结果。"""

    def evaluate(self, template_name: str) -> list[PromptEvalResult]:
        """评估各变体的效果对比。"""


class PromptMonitor:
    """Prompt 效果监控。"""

    def record_call(
        self, template_name: str, variant_name: str, version: str,
        rework_count: int, tokens: int, latency_ms: float, passed: bool,
    ):
        """记录一次调用效果。"""

    def report(self, template_name: str) -> dict:
        """生成 prompt 效果报告。"""
```

## 4. 实现方案

### 4.1 模板系统

使用 Jinja2 模板引擎（Python 生态最成熟的模板库）：

```jinja
{# prompts/role.coder.j2 #}
你是 **编码专家**，负责根据工作包规格实现代码。

## 背景
项目目标：{{ goal }}
架构方案：{{ architecture }}

## 工作包
{{ package_description }}

## 约束
- 交付物必须用 write_file 写入工作区
- 运行前先读依赖工件的代码
- 如需要第三方库，先检查是否已安装
- 缩进统一用 4 空格
```

### 4.2 迁移方案

```
阶段 1：模板文件 + 现有硬编码并存（读取模板，不存在时回退到硬编码）
阶段 2：所有角色提示词迁移到模板文件
阶段 3：废弃硬编码，统一走模板系统
```

模板文件目录结构：

```
prompts/
├── role.coder.j2          # 编码角色提示词
├── role.tester.j2         # 测试角色提示词
├── role.reviewer.j2       # 评审角色提示词
├── role.researcher.j2     # 调研角色提示词
├── chief.architecture.j2  # 首脑架构提示词
├── chief.review.j2        # 首脑评审提示词
└── templates.json         # 模板元数据（版本/作者/标签）
```

### 4.3 A/B 测试配置

```json
{
  "experiments": [
    {
      "name": "coder-prompt-v2",
      "template_name": "role.coder",
      "variants": [
        {"name": "control", "version": "1.0.0", "weight": 0.5},
        {"name": "variant_a", "version": "2.0.0", "weight": 0.3},
        {"name": "variant_b", "version": "2.1.0", "weight": 0.2}
      ],
      "metrics": ["rework_rate", "pass_rate", "avg_tokens"],
      "min_sample": 100
    }
  ]
}
```

## 5. 交付物清单

| 工件 | 位置 | 说明 |
|------|------|------|
| Prompt 注册表 | `agent_hive/prompt_management.py` | PromptRegistry + PromptTemplate + 模板引擎 |
| A/B 测试框架 | 同上 | PromptABTest + 变体管理 + 效果评估 |
| 效果监控 | 同上 | PromptMonitor + 调用记录 |
| 模板文件 | `prompts/` 目录 | 按角色/用途分离的 Jinja2 模板 |
| 迁移脚本 | `scripts/migrate_prompts.py` | 将现有硬编码 prompt 迁移到模板文件 |
| 单元测试 | `tests/test_prompt_management.py` | 覆盖注册/渲染/版本对比/A-B 测试 |
| 配置示例 | `.env.example` 补充 | `HIVE_PROMPT_DIR`、`HIVE_PROMPT_AB_CONFIG` |

## 6. 验收标准

- [ ] Prompt 模板可注册、版本化、按名称和版本检索
- [ ] 模板渲染支持变量替换，缺失变量时明确报错不静默吞掉
- [ ] 两个版本的 prompt 可 diff 对比，输出行级差异
- [ ] A/B 测试按权重随机分配变体，流量分配分布符合预期
- [ ] A/B 测试结果可对比，生成报告（返工率/通过率/token 消耗）
- [ ] 迁移后现有 prompt 行为不变（通过回归测试验证）
- [ ] 模板文件热加载（修改文件后不重启进程即可生效，方便调试）
- [ ] 不配置模板目录时，回退到现有硬编码（向后兼容）

## 7. 联动关系

| 联动卡片 | 关系 | 说明 |
|---------|------|------|
| card-model-resilience | 配合 | prompt 变体选择可结合 model fallback（不同模型用不同 prompt 版本） |
| card-cost-control | 数据源 | prompt 版本的效果数据（token 消耗）是成本控制的重要输入 |
| card-tool-registry | 配合 | 工具注册表提供工具描述，prompt 模板引用工具描述 |

## 8. 实现效果

**改造前**：改 prompt 直接改代码，改完无法对比效果，不知道是变好了还是变差了。改错了只能靠 git revert。

**改造后**：每个 prompt 版本都有记录，可以 diff 对比。"编码角色提示词 v2.0 的返工率从 30% 降到 15%"。A/B 测试可以小流量验证新 prompt 效果，确认提升后再全量上线。prompt 优化从"拍脑袋改"变成"数据驱动迭代"。