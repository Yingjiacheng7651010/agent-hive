#Requires -Version 5.1
<#
.SYNOPSIS
  对 dist 下所有 agent-hive-* 资产生成 SHA256SUMS.txt。

.DESCRIPTION
  输出格式：<hash>  <filename>（与 GNU sha256sum 兼容：小写十六进制 + 两空格）。
  默认扫描 <仓库根>/dist；可用 -DistDir 覆盖（相对路径按仓库根解析）。

  用法：
    pwsh ./scripts/release/make_checksums.ps1
    pwsh ./scripts/release/make_checksums.ps1 -DistDir dist
#>
[CmdletBinding()]
param(
  [string]$DistDir = "dist"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not [System.IO.Path]::IsPathRooted($DistDir)) {
  $DistDir = Join-Path $Root $DistDir
}
if (-not (Test-Path $DistDir)) { throw "目录不存在: $DistDir" }

$files = Get-ChildItem -Path $DistDir -File |
  Where-Object { $_.Name -like "agent-hive-*" } |
  Sort-Object Name
if (-not $files) { throw "在 $DistDir 下未找到任何 agent-hive-* 资产" }

$lines = foreach ($f in $files) {
  $hash = (Get-FileHash -Algorithm SHA256 -Path $f.FullName).Hash.ToLowerInvariant()
  "{0}  {1}" -f $hash, $f.Name
}

$out = Join-Path $DistDir "SHA256SUMS.txt"
Set-Content -Path $out -Value $lines -Encoding ascii

Write-Host "已生成: $out"
Write-Host "资产数: $($files.Count)"
$files | ForEach-Object { Write-Host "  - $($_.Name)" }
