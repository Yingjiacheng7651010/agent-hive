#Requires -Version 5.1
<#
.SYNOPSIS
  agent-hive Windows 发布构建：PyInstaller 打包 + portable zip + NSIS 安装包。

.DESCRIPTION
  1. 从 pyproject.toml 自动读取版本号（不硬编码）。
  2. 调用 PyInstaller 构建（优先 `uv run --with pyinstaller`；
     uv 不可用时退化为 .venv 内 pip install pyinstaller 后调用）。
  3. 把 dist/agent-hive/ 打成免安装 portable zip（含 agent-hive.exe）。
  4. 下载便携 NSIS 3.x（SourceForge；失败则提示手动安装并跳过 installer）。
  5. makensis 编译 scripts/release/installer.nsi 生成 setup.exe。

  产物（dist/ 下）：
    agent-hive-<ver>-windows-x86_64-portable.zip
    agent-hive-<ver>-windows-x86_64-setup.exe

  全程使用 & 调用外部程序并检查 $LASTEXITCODE。
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

# ---------------------------------------------------------------------------
# 1. 版本号：自动读取 pyproject.toml
# ---------------------------------------------------------------------------
$m = Select-String -Path (Join-Path $Root "pyproject.toml") -Pattern '^\s*version\s*=\s*"([^"]+)"' | Select-Object -First 1
if (-not $m -or -not $m.Matches[0].Groups[1].Value) {
  throw "无法从 pyproject.toml 读取 version"
}
$Version = $m.Matches[0].Groups[1].Value
Write-Host "[release] 版本: $Version"

# ---------------------------------------------------------------------------
# 2. PyInstaller 构建（one-folder -> dist/agent-hive/）
# ---------------------------------------------------------------------------
function Invoke-PyInstaller {
  $pyiArgs = @("--noconfirm", "--distpath", "dist") + @((Join-Path $PSScriptRoot "agent_hive.spec"))
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "[release] 使用 uv run --with pyinstaller ..."
    & uv run --with pyinstaller pyinstaller @pyiArgs
  } elseif (Test-Path (Join-Path $Root ".venv\Scripts\python.exe")) {
    Write-Host "[release] uv 不可用，使用 .venv 内 PyInstaller（先确保已安装）"
    & (Join-Path $Root ".venv\Scripts\python.exe") -m pip install --quiet pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "pip install pyinstaller 失败（exit=$LASTEXITCODE）" }
    & (Join-Path $Root ".venv\Scripts\python.exe") -m PyInstaller @pyiArgs
  } else {
    throw "既没有 uv 也没有 .venv，无法运行 PyInstaller"
  }
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller 构建失败（exit=$LASTEXITCODE），见上方日志" }
}

# 可选：生成 Windows 版本资源（version_info.txt，经环境变量传给 spec 的
# version= 参数；任何失败都不影响构建——版本资源可省略）
try {
  $viDir = Join-Path $Root "build\release"
  New-Item -ItemType Directory -Path $viDir -Force | Out-Null
  $v4 = @($Version.Split('.') + @("0", "0", "0"))[0..3]
  $fileversCsv = $v4 -join ", "
  $fileversDot = $v4 -join "."
  $vi = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($fileversCsv),
    prodvers=($fileversCsv),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [StringStruct('CompanyName', 'agent-hive'),
           StringStruct('FileDescription', 'agent-hive CLI'),
           StringStruct('FileVersion', '$fileversDot'),
           StringStruct('InternalName', 'agent-hive'),
           StringStruct('OriginalFilename', 'agent-hive.exe'),
           StringStruct('ProductName', 'agent-hive'),
           StringStruct('ProductVersion', '$fileversDot')]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@
  $viPath = Join-Path $viDir "version_info.txt"
  Set-Content -Path $viPath -Value $vi -Encoding ascii
  $env:AGENT_HIVE_VERSION_INFO = $viPath
  Write-Host "[release] Windows 版本资源: $viPath"
} catch {
  Write-Warning "[release] 版本资源生成失败（跳过，不影响构建）：$($_.Exception.Message)"
}

Invoke-PyInstaller

$bundle = Join-Path $Root "dist\agent-hive"
$exePath = Join-Path $bundle "agent-hive.exe"
if (-not (Test-Path $exePath)) { throw "未找到构建产物: $exePath" }
Write-Host "[release] PyInstaller 产物: $bundle"

# ---------------------------------------------------------------------------
# 3. portable zip（含顶层 agent-hive/ 目录与 agent-hive.exe）
# ---------------------------------------------------------------------------
$zipPath = Join-Path $Root "dist\agent-hive-$Version-windows-x86_64-portable.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $bundle -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "[release] portable zip: $zipPath"

# ---------------------------------------------------------------------------
# 4/5. NSIS 安装包
# ---------------------------------------------------------------------------
$tools = Join-Path $Root "build\release-tools"
$nsisDir = Join-Path $tools "nsis-3.10"
$makensis = Join-Path $nsisDir "makensis.exe"
$installerNsi = Join-Path $PSScriptRoot "installer.nsi"
$setupPath = Join-Path $Root "dist\agent-hive-$Version-windows-x86_64-setup.exe"

if (-not (Test-Path $makensis)) {
  New-Item -ItemType Directory -Path $tools -Force | Out-Null
  $nsisZip = Join-Path $tools "nsis-3.10.zip"
  $urls = @(
    "https://sourceforge.net/projects/nsis/files/NSIS%203/3.10/nsis-3.10.zip",
    "https://sourceforge.net/projects/nsis/files/NSIS%203/3.10/nsis-3.10.zip/download"
  )
  $downloaded = $false
  foreach ($u in $urls) {
    if ($downloaded) { break }
    try {
      Write-Host "[release] 下载 NSIS: $u"
      Invoke-WebRequest -Uri $u -OutFile $nsisZip -UseBasicParsing -MaximumRedirection 10
      if ((Get-Item $nsisZip).Length -gt 1MB) { $downloaded = $true }
      else { Write-Warning "[release] 下载文件过小（$((Get-Item $nsisZip).Length) bytes），疑似错误页，尝试下一个 URL" }
    } catch {
      Write-Warning "[release] NSIS 下载失败: $($_.Exception.Message)"
    }
  }
  if ($downloaded) {
    Expand-Archive -Path $nsisZip -DestinationPath $tools -Force
  }
}

if (-not (Test-Path $makensis)) {
  # 下载失败：按契约退化——提示用户手动安装 NSIS 并跳过 installer（不失败退出）
  Write-Warning "======================================================"
  Write-Warning "[release] 便携 NSIS 下载失败，跳过 installer 生成（portable zip 已就绪）。"
  Write-Warning "[release] 请手动安装 NSIS 3.x（https://nsis.sourceforge.io/Download）后执行："
  Write-Warning "  makensis /DVERSION=$Version /DDIST_DIR=$($bundle -replace '\\','/') /DOUT_DIR=$((Join-Path $Root 'dist') -replace '\\','/') $installerNsi"
  Write-Warning "======================================================"
} else {
  $distDirFwd = $bundle -replace "\\", "/"
  $outDirFwd = (Join-Path $Root "dist") -replace "\\", "/"
  & $makensis "/DVERSION=$Version" "/DDIST_DIR=$distDirFwd" "/DOUT_DIR=$outDirFwd" $installerNsi
  if ($LASTEXITCODE -ne 0) { throw "makensis 失败（exit=$LASTEXITCODE），见上方日志" }
  if (-not (Test-Path $setupPath)) { throw "未生成安装包: $setupPath" }
  Write-Host "[release] NSIS 安装包: $setupPath"
}

# ---------------------------------------------------------------------------
# 输出汇总
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "==================== Windows 构建完成 ===================="
Write-Host "版本:      $Version"
Write-Host "portable:  $zipPath"
if (Test-Path $setupPath) {
  Write-Host "setup:     $setupPath"
} else {
  Write-Host "setup:     （未生成——见上方 NSIS 提示）"
}
