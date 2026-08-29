# 发布流程 / 平台覆盖 / 安装与校验说明

> 适用读者：维护者（发布流程）与用户（安装/校验）。
> **版本现状**：`pyproject.toml` 版本已提升为 `0.2.0`，**v0.2.0 即将发布**，是首个附带三平台安装包的版本（仓库当前尚无 tag，v0.2.0 将是首个 tag）；`hive_security` / `hive_cost` 组件版本为 `0.1.0`。
> **未上 PyPI**：`hive-security` / `hive-cost` 尚未发布到 PyPI（发布工作流已就绪，见下文「发布流程」）；TestFlight 属于路线图而非现状。

## 1. 发布流程（给维护者）

以 v0.2.0 为例，按顺序执行：

1. **版本提升**：修改 `pyproject.toml` 的 `version = "0.2.0"`（同步 `hive_security/pyproject.toml`、`hive_cost/pyproject.toml` 如涉及组件版本）。
2. **本地验收**：运行 `uv run python scripts/verify.py`（pytest + compileall + contract 漂移检查 + contract-lint + security golden 一键验收）；再跑 `uv run python scripts/release_check.py` 做发布预检（README / 官网链接完整性 + 工作流 YAML 解析 + 仓库内无密钥红线自查）。
3. **本地构建 Windows 安装包（可选）**：使用 `.tools/nsis.zip`（NSIS）本地先行构建 `setup.exe`，确认安装流程无误（CI 三平台构建见第 5 步）。
4. **推送 main**：确认主分支 CI 通过（`pages.yml` 会同步更新 GitHub Pages 官网）。
5. **打 tag 并推送**：`git tag v0.2.0` → `git push origin v0.2.0`。推送 `v*` tag 触发：
   - **GitHub Releases 三平台构建**（随 v0.2.0 落地）：CI 自动构建 Windows / Linux / macOS 安装包与压缩包，并附加到 GitHub Release；
   - **PyPI 发布**（`publish-packages.yml`）：`uv build` 产出 `hive-security` / `hive-cost` 的 wheel + sdist，经 Trusted Publishing（OIDC，仓库内零 token）发布；**若 PyPI 上尚未创建这两个项目，publish job 自动跳过（属预期，不报错）**。
6. **校验资产**：到 GitHub Release 页面核对全部资产 + `SHA256SUMS.txt`，用第 4 节命令抽验。

> **现状说明**：当前 `.github/workflows/` 只有 `publish-packages.yml`（PyPI）与 `pages.yml`（GitHub Pages）；三平台安装包的 CI 构建工作流是 v0.2.0 的落地内容，落地前 Windows 安装包可本地先行构建。

## 2. 资产清单

GitHub Release 资产（`<ver>` 以实际 tag 为准，如 `v0.2.0`）：

| 平台 | 文件名 | 用途 |
|---|---|---|
| Windows | `agent-hive-<ver>-windows-x86_64-setup.exe` | 安装包（NSIS），双击安装 |
| Windows | `agent-hive-<ver>-windows-x86_64-portable.zip` | 免安装压缩包，解压即用 |
| Linux | `agent-hive-<ver>-linux-x86_64.AppImage` | 单文件应用，`chmod +x` 后运行 |
| Linux | `agent-hive-<ver>-linux-x86_64.tar.gz` | 免安装压缩包，解压即用 |
| macOS | `agent-hive-<ver>-macos-<arch>.dmg` | 磁盘映像（arch = universal2 / arm64 / x86_64，以实测为准），拖入 Applications |
| macOS | `agent-hive-<ver>-macos.tar.gz` | 免安装压缩包，解压即用 |
| Python | `agent-hive-<ver>-py3-none-any.whl` | pip wheel（`pip install`） |
| Python | `agent-hive-<ver>.tar.gz` | sdist（源码包） |
| 全部 | `SHA256SUMS.txt` | 全部资产的 SHA-256 校验和（见第 4 节） |

PyPI 资产（`publish-packages.yml` 产出，发布后于 pypi.org 获取）：

| 包 | 资产 |
|---|---|
| `hive-security` | `hive_security-0.1.0-py3-none-any.whl` + `hive_security-0.1.0.tar.gz` |
| `hive-cost` | `hive_cost-0.1.0-py3-none-any.whl` + `hive_cost-0.1.0.tar.gz` |

## 3. 安装说明（分平台）

### Windows

- **setup.exe**：双击 `agent-hive-<ver>-windows-x86_64-setup.exe`，按向导安装；安装后从开始菜单/桌面快捷方式启动。
- **portable.zip**：解压到任意目录（如 `C:\agent-hive\`），双击目录内主程序即可运行，无需安装。

### Linux

- **AppImage**：

  ```bash
  chmod +x agent-hive-<ver>-linux-x86_64.AppImage
  ./agent-hive-<ver>-linux-x86_64.AppImage
  ```

  FUSE 缺失报错时（常见于精简发行版/Docker），改用解包运行：

  ```bash
  ./agent-hive-<ver>-linux-x86_64.AppImage --appimage-extract-and-run
  ```

  或安装 `libfuse2`（Debian/Ubuntu：`sudo apt install libfuse2`）。
- **tar.gz**：`tar -xzf agent-hive-<ver>-linux-x86_64.tar.gz` 后运行解压目录内主程序。

### macOS

- **dmg**：打开 `agent-hive-<ver>-macos.dmg`，把应用拖入「应用程序」文件夹。
- **右键打开绕过 Gatekeeper**：若提示「无法验证开发者」（未签名/未公证产物），在「访达」中**右键 → 打开**并确认；或终端执行 `xattr -dr com.apple.quarantine /Applications/agent-hive.app`（自行评估风险后使用）。
- **tar.gz**：`tar -xzf agent-hive-<ver>-macos.tar.gz` 后运行主程序。

### Python（pip / uv）

```bash
# pip
pip install agent-hive          # 或指定版本：pip install agent-hive==<ver>
# uv（推荐）
uv pip install agent-hive
# 安装后验证
agent-hive --help
```

依赖组件（发布后可用）：

```bash
pip install hive-security hive-cost   # 架构安全验证 + 成本预算/熔断
```

> 从源码运行（开发模式）：`git clone <repo>` 后 `uv sync`，用 `uv run python -m agent_hive run --goal "..."` 启动首脑（需按 README 配置 `.env` 密钥）。

## 4. 校验（SHA256SUMS.txt）

下载资产与 `SHA256SUMS.txt` 后，在**同一目录**下执行：

**Windows（PowerShell）**

```powershell
# 单文件对比
(Get-FileHash .\agent-hive-<ver>-windows-x86_64-setup.exe -Algorithm SHA256).Hash -eq `
  ((Get-Content .\SHA256SUMS.txt | Select-String 'setup.exe').ToString().Split()[0])
# 输出 True 即一致
```

**Linux / macOS**

```bash
# 校验清单内全部文件（输出每个文件的 OK / FAILED）
sha256sum -c SHA256SUMS.txt
```

> 校验通过后再安装；任何「FAILED」都说明下载损坏或被篡改，请重新下载并核对来源。

## 5. iOS 安装

- **现状（官方渠道）**：官网是 PWA（<https://yingjiacheng7651010.github.io/agent-hive/>）。在 **Safari** 中打开官网 → 点「分享」按钮 → **「添加到主屏幕」**，即可在主屏幕获得应用图标，像原生应用一样启动。
- **路线图（非现状）**：TestFlight 内测版 iOS 应用属于后续规划，当前**不提供** TestFlight 渠道，请以官网 PWA 为准。

## 6. 常见问题（FAQ）

| 问题 | 说明与处理 |
|---|---|
| **AppImage 打不开** | 先 `chmod +x`；报 FUSE 相关错误时用 `--appimage-extract-and-run` 解包运行，或安装 `libfuse2` |
| **macOS「无法验证开发者」** | 未签名/未公证产物的正常提示：访达中右键 → 打开，或 `xattr -dr com.apple.quarantine <app>`（自行评估风险） |
| **exe 被杀毒软件误报** | 产物**未做代码签名**（Authenticode 签名属于后续规划），Windows Defender/第三方杀软可能误报；请先用 `SHA256SUMS.txt` 核对哈希，确认无误后加入信任/白名单 |
| **CI 构建失败排查** | ① GitHub Actions 页面查看对应 workflow run 日志；② 本地先跑 `uv run python scripts/release_check.py`（链接/工作流预检）与 `uv run python scripts/verify.py`（全量验收）；③ 确认 tag 格式为 `vX.Y.Z` 且已推送；④ PyPI publish 显示跳过是「项目未在 PyPI 创建」的正常行为，不是失败 |
| **PyPI 装不了 hive-security / hive-cost** | 两包**尚未发布**到 PyPI（路线图项，工作流已就绪）；发布前请用仓库内 `uv build` 本地构建，或从源码 `uv sync` 使用 |
| **想用 TestFlight** | 暂无；当前 iOS 官方渠道是官网 PWA「添加到主屏幕」（见第 5 节） |
