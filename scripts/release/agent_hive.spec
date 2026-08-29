# -*- mode: python ; coding: utf-8 -*-
"""agent-hive PyInstaller 构建 spec（Windows / Linux / macOS 三平台共用）。

统一调用方式（各平台构建脚本都这样用）：
    uv run --with pyinstaller pyinstaller scripts/release/agent_hive.spec --noconfirm --distpath dist

产物：one-folder 模式 -> dist/agent-hive/（内含可执行文件与 _internal/）。
      Windows 下可执行文件为 agent-hive.exe（console 程序）。

关键设计（请勿在未理解的情况下删除）：
1. 入口：不使用 agent_hive/__main__.py 作为入口——它含相对导入
   （from .main import main），冻结后运行时抛
   "attempted relative import with no known parent package"（已实测）。
   因此本 spec 在 gitignore 的 build/ 目录生成一个仅含绝对导入的
   bootstrap 入口脚本（build/agent_hive_entry.py），Analysis 分析它。
2. collect 清单（COLLECT_PACKAGES，理由见下方内联注释）：langchain 全家桶
   与 langgraph 大量使用延迟/动态导入，静态分析抓不全，必须
   collect_submodules / collect_all。
3. hiddenimports 补齐常见缺口：sqlite3（checkpoint 直接使用）、
   anyio/httpx 等 HTTP/异步栈、openai SDK（langchain_deepseek 经它调用）。
4. excludes 剔除 tkinter/测试框架等无用模块，减小体积；刻意不排除
   numpy/pandas/scipy（langchain_community 有子模块引用，排除会导致失败）。
5. Windows 版本资源：可选。构建脚本（build_windows.ps1）若生成了
   version_info.txt 并通过 AGENT_HIVE_VERSION_INFO 环境变量传入，则挂到
   exe 上；未设置时 version=None，不影响构建。
6. macOS 目标架构：spec 模式下 CLI 的 --target-architecture 会被忽略，
   因此通过 AGENT_HIVE_TARGET_ARCH 环境变量传入
   （universal2 / arm64 / x86_64），由 EXE(target_arch=...) 生效；
   未设置时用本机架构。build_macos.sh 负责设置该变量并按 lipo 实测命名。
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# SPECPATH 是 PyInstaller 注入的全局（spec 所在目录）；此处兜底便于直接 py_compile
SPEC_DIR = globals().get("SPECPATH") or os.path.dirname(os.path.abspath(__file__))
# 项目根目录（scripts/release 的上一级）
ROOT = os.path.abspath(os.path.join(SPEC_DIR, os.pardir, os.pardir))

# ---------------------------------------------------------------------------
# collect 清单与理由：
# - langchain / langchain_core / langchain_community：langchain 1.x 通过
#   langchain_core 的注册机制与大量动态 import（agent/llm 工厂、工具注册），
#   静态分析抓不全，必须 collect_submodules + 收集数据文件。
# - langchain_deepseek / langchain_tavily：DeepSeek（OpenAI 兼容）/Tavily
#   provider 包，内部动态加载模型/检索器。
# - langgraph / langgraph_checkpoint / langgraph_checkpoint_sqlite：
#   LangGraph 节点/检查点按字符串名字动态导入；checkpoint_sqlite 的
#   SqliteSaver 是运行必需（agent_hive/main.py 直接使用）。
# - pydantic：模型定义用到 __get_pydantic_core_schema__ 等动态机制，
#   pydantic_core 二进制必须随包打包。
# - dotenv / jinja2：main.py 直接 import；jinja2 有数据文件与延迟加载。
# - hive_security / hive_cost：本地 path 依赖（src 布局，editable 安装），
#   collect 确保按实际包布局打进包。
# - agent_hive：本项目自身（含 prompts 等资源文件）。
# ---------------------------------------------------------------------------
COLLECT_PACKAGES = [
    "langchain",
    "langchain_core",
    "langchain_community",
    "langchain_deepseek",
    "langchain_tavily",
    "langgraph",
    "langgraph_checkpoint",
    "langgraph_checkpoint_sqlite",
    "pydantic",
    "dotenv",
    "jinja2",
    "hive_security",
    "hive_cost",
    "agent_hive",
]

datas = []
binaries = []
hiddenimports = []

for _pkg in COLLECT_PACKAGES:
    try:
        _d, _b, _h = collect_all(_pkg)
    except Exception:
        # 个别包（如精简环境下的可选依赖）collect_all 失败时，退化为
        # collect_submodules + 数据文件；再失败则跳过该包，不阻断构建。
        try:
            _h = collect_submodules(_pkg)
            _d = collect_data_files(_pkg)
            _b = []
        except Exception:
            _d, _b, _h = [], [], []
    # 注意：用 += 追加到新的组合列表（collect_all 返回的列表会被
    # PyInstaller 在分析期原地修改，不能直接复用为 Analysis 的入参）。
    datas += _d
    binaries += _b
    hiddenimports += _h

# ---------------------------------------------------------------------------
# 常见动态导入缺口（即便个别未安装也只会告警，不会失败）
# ---------------------------------------------------------------------------
hiddenimports += [
    "sqlite3",               # checkpoint 直接使用
    "anyio", "sniffio",      # langchain 流式/异步
    "httpx", "httpcore", "h11", "socksio",  # Tavily / OpenAI 兼容 SDK 的 HTTP 栈
    "openai",                # langchain_deepseek 经由 OpenAI SDK
    "tiktoken",              # 模型 token 计数（延迟加载）
    "requests", "urllib3",
    "charset_normalizer", "certifi", "idna",
    "yaml",                  # 配置/工具可能用到
    "pydantic_core", "typing_extensions", "annotated_types",
    "multipart",             # OpenAI SDK 上传用
    "jsonpatch",             # langchain_core 运行时补丁
    "importlib_metadata",
]

# ---------------------------------------------------------------------------
# 无用/重型模块排除（减小体积）。刻意不排除 numpy/pandas/scipy：
# langchain_community 有子模块引用它们，排除会导致构建/运行失败。
# ---------------------------------------------------------------------------
excludes = [
    "tkinter",
    "unittest",
    "pytest",
    "test",
    "doctest",
    "PySide6",
    "PyQt5",
    "PyQt6",
    "IPython",
    "jupyter",
    "notebook",
    "matplotlib",
]

# ---------------------------------------------------------------------------
# 入口 bootstrap（绝对导入，规避 __main__.py 相对导入的冻结问题）
# ---------------------------------------------------------------------------
_BUILD_DIR = os.path.join(ROOT, "build")
os.makedirs(_BUILD_DIR, exist_ok=True)
ENTRY = os.path.join(_BUILD_DIR, "agent_hive_entry.py")
if not os.path.exists(ENTRY):
    with open(ENTRY, "w", encoding="utf-8") as _f:
        _f.write(
            "from agent_hive.main import main\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )

# ---------------------------------------------------------------------------
# macOS 目标架构（CLI 的 --target-architecture 在 spec 模式下被忽略，
# 故用环境变量传入；Windows/Linux 不设置 -> 本机架构）
# ---------------------------------------------------------------------------
_target_arch = os.environ.get("AGENT_HIVE_TARGET_ARCH") or None

# ---------------------------------------------------------------------------
# Windows 版本资源（可选：build_windows.ps1 生成 version_info.txt 后经
# AGENT_HIVE_VERSION_INFO 传入；省略时 version=None，不影响构建）
# ---------------------------------------------------------------------------
_version_resource = None
_vi_path = os.environ.get("AGENT_HIVE_VERSION_INFO")
if _vi_path and os.path.isfile(_vi_path):
    _version_resource = _vi_path

a = Analysis(
    [ENTRY],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="agent-hive",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # 不启用 UPX，保持稳定可复现
    console=True,            # CLI 是控制台程序
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=_target_arch,  # macOS: universal2/arm64/x86_64；其他平台 None
    codesign_identity=None,
    entitlements_file=None,
    version=_version_resource,  # Windows 版本资源（可选，见上）
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="agent-hive",
)
