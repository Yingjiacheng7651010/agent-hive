#!/usr/bin/env bash
# =============================================================================
# agent-hive macOS 发布构建：PyInstaller(one-folder) + dmg + tar.gz
#
# 用法: bash scripts/release/build_macos.sh   （在仓库根目录任意位置执行均可）
#
# 目标架构策略：
#   优先 universal2（Intel + Apple Silicon），构建或校验失败时回退本机架构。
#   注意：PyInstaller 以 spec 模式运行时，CLI 的 --target-architecture 会被
#   忽略，因此本脚本通过 AGENT_HIVE_TARGET_ARCH 环境变量把架构传给 spec 的
#   EXE(target_arch=...)。产物架构以 `lipo -archs` 实测为准，保证文件名里的
#   <arch>（universal2 / arm64 / x86_64）与真实二进制一致。
#
# 产物（dist/ 下）：
#   agent-hive-<ver>-macos-<arch>.dmg
#   agent-hive-<ver>-macos-<arch>.tar.gz
#
# 说明：PyInstaller 6.x 在 macOS 上会默认对 bootloader 做 ad-hoc 签名，使其
# 能在 Apple Silicon 上运行；正式签名（Developer ID）与公证（notarytool）
# 超出本工作包范围，集成阶段按需补充。
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# ---- 1. 版本号（自动读取 pyproject.toml，不硬编码）----
VERSION="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' pyproject.toml | head -n1)"
if [ -z "$VERSION" ]; then
  echo "error: 无法从 pyproject.toml 读取 version" >&2
  exit 1
fi
echo "[release] 版本: $VERSION"

NATIVE_ARCH="$(uname -m)"   # arm64 或 x86_64

# ---- 2. PyInstaller 构建（$1 = AGENT_HIVE_TARGET_ARCH，空串=本机架构）----
run_pyinstaller() {
  rm -rf dist/agent-hive build/agent-hive
  if command -v uv >/dev/null 2>&1; then
    AGENT_HIVE_TARGET_ARCH="${1:-}" uv run --with pyinstaller \
      pyinstaller --noconfirm --distpath dist scripts/release/agent_hive.spec
  else
    python3 -c "import PyInstaller" 2>/dev/null || python3 -m pip install --quiet pyinstaller
    AGENT_HIVE_TARGET_ARCH="${1:-}" python3 -m PyInstaller \
      --noconfirm --distpath dist scripts/release/agent_hive.spec
  fi
}

# ---- 3. 尝试 universal2；失败或产物非双架构则回退本机架构 ----
MAC_ARCH=""
if run_pyinstaller "universal2"; then
  if [ -x "dist/agent-hive/agent-hive" ] && command -v lipo >/dev/null 2>&1; then
    ARCHS="$(lipo -archs dist/agent-hive/agent-hive 2>/dev/null || true)"
    case "$ARCHS" in
      *arm64*x86_64*|*x86_64*arm64*) MAC_ARCH="universal2" ;;
      *"$NATIVE_ARCH"*)              MAC_ARCH="$NATIVE_ARCH" ;;  # 双架构未生效，产物即本机架构
      *)                             MAC_ARCH="" ;;
    esac
  fi
fi

if [ -z "$MAC_ARCH" ]; then
  echo "[release] universal2 不可行，回退本机架构 $NATIVE_ARCH" >&2
  run_pyinstaller ""
  MAC_ARCH="$NATIVE_ARCH"
fi

BIN="dist/agent-hive/agent-hive"
if [ ! -x "$BIN" ]; then
  echo "error: 未找到构建产物 $BIN" >&2
  exit 1
fi

# ---- 4. dmg（UDZO 压缩映像，卷名 agent-hive）----
DMG_OUT="dist/agent-hive-${VERSION}-macos-${MAC_ARCH}.dmg"
hdiutil create -volname "agent-hive" -srcfolder dist/agent-hive -ov -format UDZO "$DMG_OUT"

# ---- 5. tar.gz（便携版，含顶层 agent-hive/ 目录）----
TAR_OUT="dist/agent-hive-${VERSION}-macos-${MAC_ARCH}.tar.gz"
tar -czf "$TAR_OUT" -C dist agent-hive

echo ""
echo "==================== macOS 构建完成 ===================="
echo "版本:      $VERSION"
echo "架构:      $MAC_ARCH"
echo "dmg:       $DMG_OUT"
echo "tar.gz:    $TAR_OUT"
