#!/usr/bin/env bash
# =============================================================================
# agent-hive Linux 发布构建：PyInstaller(one-folder) + AppDir/AppImage + tar.gz
#
# 用法: bash scripts/release/build_linux.sh   （在仓库根目录任意位置执行均可）
# 前置: python3 + uv（或已装 pyinstaller 的 venv）；可联网下载 appimagetool。
#
# 产物（dist/ 下）：
#   agent-hive-<ver>-linux-x86_64.AppImage
#   agent-hive-<ver>-linux-x86_64.tar.gz
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

# ---- 2. PyInstaller 构建（one-folder -> dist/agent-hive/）----
if command -v uv >/dev/null 2>&1; then
  echo "[release] 使用 uv run --with pyinstaller ..."
  uv run --with pyinstaller pyinstaller --noconfirm --distpath dist scripts/release/agent_hive.spec
else
  echo "[release] uv 不可用，使用 python3 -m PyInstaller（未安装则先 pip install）"
  python3 -c "import PyInstaller" 2>/dev/null || python3 -m pip install --quiet pyinstaller
  python3 -m PyInstaller --noconfirm --distpath dist scripts/release/agent_hive.spec
fi

BIN="dist/agent-hive/agent-hive"
if [ ! -x "$BIN" ]; then
  echo "error: 未找到构建产物 $BIN" >&2
  exit 1
fi

# ---- 3. 组装 AppDir ----
# 布局：usr/bin/agent-hive（可执行文件）+ usr/bin/_internal（PyInstaller 运行时，
#       必须与可执行文件同目录）+ usr/share/applications/agent-hive.desktop
#       + usr/share/icons/...（占位图标，正式发布请替换真实图标）。
# 注：把 PyInstaller 目录扁平化进 usr/bin/ 而非放进子目录，是为了让
#     .desktop 的 Exec=agent-hive 能直接被 appimagetool 解析到可执行文件。
APPDIR="build/appdir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -a dist/agent-hive/. "$APPDIR/usr/bin/"

cat > "$APPDIR/usr/share/applications/agent-hive.desktop" <<'EOF'
[Desktop Entry]
Name=agent-hive
Comment=Multi-agent orchestration CLI (chief + specialists on LangGraph)
Comment[zh_CN]=首脑统筹的多智能体编排 CLI
Exec=agent-hive
Terminal=true
Type=Application
Categories=Development;Utility;ConsoleOnly;
Icon=agent-hive
StartupNotify=false
EOF

# 占位图标（1x1 透明 PNG，base64 内嵌；正式发布请替换为真实图标）
if command -v base64 >/dev/null 2>&1; then
  printf '%s' 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==' \
    | base64 -d > "$APPDIR/usr/share/icons/hicolor/256x256/apps/agent-hive.png"
fi

# AppRun：显式定位本 AppDir 内可执行文件，不依赖 PATH
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
SELF="$(readlink -f "$0")"
HERE="${SELF%/*}"
exec "${HERE}/usr/bin/agent-hive" "$@"
EOF
chmod +x "$APPDIR/AppRun" "$APPDIR/usr/bin/agent-hive"

# ---- 4. appimagetool 生成 .AppImage ----
TOOLS="build/release-tools"
mkdir -p "$TOOLS"
APPIMAGETOOL="$TOOLS/appimagetool-x86_64.AppImage"
if [ ! -x "$APPIMAGETOOL" ]; then
  echo "[release] 下载 appimagetool ..."
  curl -fL --retry 3 -o "$APPIMAGETOOL" \
    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$APPIMAGETOOL"
fi

APPIMAGE_OUT="dist/agent-hive-${VERSION}-linux-x86_64.AppImage"
# --appimage-extract-and-run：避免依赖 FUSE，容器/CI 环境下也能运行 appimagetool
"$APPIMAGETOOL" --appimage-extract-and-run "$APPDIR" "$APPIMAGE_OUT"

# ---- 5. tar.gz（便携版，含顶层 agent-hive/ 目录）----
TAR_OUT="dist/agent-hive-${VERSION}-linux-x86_64.tar.gz"
tar -czf "$TAR_OUT" -C dist agent-hive

echo ""
echo "==================== Linux 构建完成 ===================="
echo "版本:      $VERSION"
echo "AppImage:  $APPIMAGE_OUT"
echo "tar.gz:    $TAR_OUT"
