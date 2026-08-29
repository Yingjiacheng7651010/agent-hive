; =============================================================================
; agent-hive NSIS 安装脚本（NSIS 3.x）
;
; 由 scripts/release/build_windows.ps1 调用：
;   makensis /DVERSION=<ver> /DDIST_DIR=<dist\agent-hive> /DOUT_DIR=<dist> installer.nsi
;
; 三个 define 均有默认值，便于单独调试；正式构建时一律由脚本传入。
; VERSION 必须为 x.y.z 三段式（pyproject.toml 的 version），安装包名与
; 版本资源会按 ${VERSION}.0 拼成 4 段式。
; =============================================================================

!ifndef VERSION
  !define VERSION "0.0.0"
!endif
!ifndef DIST_DIR
  !define DIST_DIR "..\..\dist\agent-hive"
!endif
!ifndef OUT_DIR
  !define OUT_DIR "..\..\dist"
!endif

!define APP_NAME "agent-hive"
!define APP_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

Name "${APP_NAME} ${VERSION}"
OutFile "${OUT_DIR}\agent-hive-${VERSION}-windows-x86_64-setup.exe"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKLM "${APP_UNINST_KEY}" "InstallLocation"
RequestExecutionLevel admin
Unicode true
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

; 安装包自身的版本信息（4 段式；VERSION 为三段式，故补 .0）
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "FileDescription" "agent-hive installer"
VIAddVersionKey "FileVersion" "${VERSION}.0"
VIAddVersionKey "ProductVersion" "${VERSION}.0"
VIAddVersionKey "LegalCopyright" "agent-hive"

!include "MUI2.nsh"
!include "WinMessages.nsh"

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; ---------------------------------------------------------------------------
; 主程序（必装，不可取消勾选）
; ---------------------------------------------------------------------------
Section "agent-hive（主程序）" SEC_MAIN
  SectionIn RO
  SetOutPath "$INSTDIR"
  ; 递归拷贝 dist\agent-hive\ 全部内容（含 _internal）
  File /r "${DIST_DIR}\*.*"

  ; 卸载器
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; 控制面板「卸载或更改程序」注册表项
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayName" "${APP_NAME} ${VERSION}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "Publisher" "agent-hive"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "DisplayIcon" "$INSTDIR\agent-hive.exe"
  WriteRegStr HKLM "${APP_UNINST_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "${APP_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKLM "${APP_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${APP_UNINST_KEY}" "NoRepair" 1

  ; 开始菜单快捷方式（CLI 为控制台程序，工作目录取 $INSTDIR 即可）
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\agent-hive.exe"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

; ---------------------------------------------------------------------------
; 可选：把安装目录加入 PATH（当前用户级 HKCU\Environment，免管理员写 HKLM）
; 默认不勾选（Section /o）。
; ---------------------------------------------------------------------------
Section /o "将 ${APP_NAME} 加入 PATH（当前用户）" SEC_PATH
  Call AddToPath
SectionEnd

; =============================================================================
; 卸载
; =============================================================================
Section "Uninstall"
  ; 删除开始菜单快捷方式
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  ; 尽力从当前用户 PATH 移除 $INSTDIR（best-effort，见 un.RemoveFromPath）
  Call un.RemoveFromPath

  ; 删除卸载注册表项与安装目录
  DeleteRegKey HKLM "${APP_UNINST_KEY}"
  RMDir /r "$INSTDIR"
  RMDir "$INSTDIR"
SectionEnd

; =============================================================================
; 函数区
; 约定：调用者先 Push 第一个参数、最后 Push 最后一个参数（栈顶为最后参数）；
;       函数结束时栈上只剩返回值（调用者 Pop 一次）。
; =============================================================================

; ---------------------------------------------------------------------------
; StrStrPos：在 haystack 中从 start 起查找 needle，返回偏移；未找到返回 -1。
; 用法：Push <haystack>; Push <needle>; Push <start>; Call StrStrPos; Pop $x
; ---------------------------------------------------------------------------
Function StrStrPos
  ; 取参（进栈顺序: [start, needle, haystack]，栈顶=start）
  Exch $2                 ; $2 = start
  Exch
  Exch $0                 ; $0 = needle
  Exch 2
  Exch $1                 ; $1 = haystack
  ; 此时栈: [old$0, old$1, old$2]（函数结束前逐一恢复）
  Push $3
  Push $4
  Push $5
  Push $6
  Push $R0
  StrLen $3 $1            ; $3 = haystack 长度
  StrCpy $6 "-1"          ; $6 = 结果偏移，默认 -1
  StrCmp $0 "" done       ; 空 needle -> 未找到
  StrCpy $4 $2            ; $4 = 扫描偏移
loop:
  IntCmp $4 $3 done 0 done ; $4 >= 长度 -> 未找到（防越界死循环）
  StrCpy $R0 $1 $3 $4     ; 取 haystack[$4 .. $4+len)（越界自动截断，截断串必然不相等）
  StrCmp $R0 $0 found
  IntOp $4 $4 + 1
  Goto loop
found:
  StrCpy $6 $4
done:
  StrCpy $0 $6            ; 结果放进 $0
  Pop $R0
  Pop $6
  Pop $5
  Pop $4
  Pop $3
  Pop $1                  ; 恢复 $1
  Pop $2                  ; 恢复 $2
  Exch $0                 ; 栈顶换为结果，$0 恢复为旧值
FunctionEnd

; ---------------------------------------------------------------------------
; AddToPath：把 $INSTDIR 追加到当前用户 PATH（HKCU\Environment）。
; 按 ';' 分词逐项比较，已存在则跳过；不会破坏其他 PATH 项。
; 注意：StrCmp 为大小写敏感比较，Windows PATH 大小写不敏感属已知边界——
; 安装时写入的路径与 $INSTDIR 完全一致，正常情况能正确命中。
; ---------------------------------------------------------------------------
Function AddToPath
  ReadRegStr $0 HKCU "Environment" "Path"
  StrCpy $1 "$INSTDIR"
  StrCpy $2 "0"           ; 扫描偏移
  StrCpy $6 "0"           ; 是否已存在（0/1）
loop:
  Push "$0"               ; haystack
  Push ";"                ; needle
  Push "$2"               ; start
  Call StrStrPos
  Pop $4                  ; 下一个 ';' 的位置，-1 = 没有
  StrCmp $4 "-1" last_entry
  IntOp $3 $4 - $2        ; 当前 token 长度
  StrCpy $5 $0 $3 $2      ; 取出当前 token
  StrCmp $5 "$1" found_existing
  IntOp $2 $4 + 1         ; 跳过 ';' 继续
  Goto loop
last_entry:
  StrCpy $5 $0 "" $2      ; 最后一段（无 ';' 结尾）
  StrCmp $5 "$1" found_existing
  Goto append
found_existing:
  StrCpy $6 "1"
append:
  StrCmp $6 "1" done      ; 已存在，跳过写入
  StrCmp $0 "" first
  StrCpy $0 "$0;$1"
  Goto write
first:
  StrCpy $0 "$1"
write:
  WriteRegExpandStr HKCU "Environment" "Path" "$0"
  ; 通知系统刷新环境变量（30 秒超时，避免卡住安装流程）
  SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=30000
done:
FunctionEnd

; ---------------------------------------------------------------------------
; un.StrStrPos：卸载段专用副本（NSIS 规定卸载段内只能调用 un.* 函数，
; 因此不能直接复用安装段的 StrStrPos）。逻辑与 StrStrPos 完全一致：
; Push <haystack>; Push <needle>; Push <start>; Call un.StrStrPos; Pop $x
; ---------------------------------------------------------------------------
Function un.StrStrPos
  Exch $2                 ; $2 = start
  Exch
  Exch $0                 ; $0 = needle
  Exch 2
  Exch $1                 ; $1 = haystack
  Push $3
  Push $4
  Push $5
  Push $6
  Push $R0
  StrLen $3 $1            ; $3 = haystack 长度
  StrCpy $6 "-1"          ; $6 = 结果偏移，默认 -1
  StrCmp $0 "" done       ; 空 needle -> 未找到
  StrCpy $4 $2            ; $4 = 扫描偏移
loop:
  IntCmp $4 $3 done 0 done ; $4 >= 长度 -> 未找到（防越界死循环）
  StrCpy $R0 $1 $3 $4     ; 取 haystack[$4 .. $4+len)（越界自动截断，截断串必然不相等）
  StrCmp $R0 $0 found
  IntOp $4 $4 + 1
  Goto loop
found:
  StrCpy $6 $4
done:
  StrCpy $0 $6            ; 结果放进 $0
  Pop $R0
  Pop $6
  Pop $5
  Pop $4
  Pop $3
  Pop $1
  Pop $2
  Exch $0                 ; 栈顶换为结果，$0 恢复为旧值
FunctionEnd

; ---------------------------------------------------------------------------
; un.RemoveFromPath：从当前用户 PATH 移除 $INSTDIR（卸载段专用——NSIS 规定
; 卸载段内只能调用以 "un." 开头的函数）。
; 按 ';' 分词逐项精确匹配后重建 PATH；不会误删包含 $INSTDIR 子路径的其他项。
; best-effort 实现（大小写敏感比较，与 AddToPath 对称）。
; ---------------------------------------------------------------------------
Function un.RemoveFromPath
  ReadRegStr $0 HKCU "Environment" "Path"
  StrCmp $0 "" done
  StrCpy $1 "$INSTDIR"
  StrCpy $2 "0"           ; 扫描偏移
  StrCpy $6 ""            ; 重建后的 PATH
loop:
  Push "$0"
  Push ";"
  Push "$2"
  Call un.StrStrPos
  Pop $4
  StrCmp $4 "-1" last_entry
  IntOp $3 $4 - $2
  StrCpy $5 $0 $3 $2
  StrCmp $5 "$1" skip
  StrCmp $6 "" 0 add_sep
  StrCpy $6 "$5"
  Goto advance
add_sep:
  StrCpy $6 "$6;$5"
  Goto advance
skip:
advance:
  IntOp $2 $4 + 1
  Goto loop
last_entry:
  StrCpy $5 $0 "" $2
  StrCmp $5 "" write
  StrCmp $5 "$1" write
  StrCmp $6 "" 0 add_sep_last
  StrCpy $6 "$5"
  Goto write
add_sep_last:
  StrCpy $6 "$6;$5"
write:
  StrCmp $6 "" wipe
  WriteRegExpandStr HKCU "Environment" "Path" "$6"
  SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=30000
  Goto done
wipe:
  DeleteRegValue HKCU "Environment" "Path"
done:
FunctionEnd
