@echo off
REM ===========================================================================
REM  File .bat PHAI thuan ASCII - xem ghi chu dau SETUP.bat.
REM ===========================================================================
REM
REM  VI SAO CO FILE NAY
REM
REM  Khi tool hong tren MAY KHACH, nguoi sua khong nhin duoc may do. Ngay
REM  13/08/2026 da mat vai luot doan sai lien tiep chi vi thieu bon con so:
REM  loi tat tro vao dau, claude nam o dau, extension da cai chua, cau hinh
REM  dang tro ve dau. Doan thi re, doan SAI thi khach cho ca ngay.
REM
REM  File nay khong sua gi ca. No chi doc va in ra, de khach chup mot tam anh
REM  gui lai. Khong sua gi la co y: mot cong cu chan doan ma tu sua thi lan sau
REM  khong ai dam chay no.
chcp 65001 >nul
cd /d "%~dp0"
title My Tool - Kiem tra may
echo ============================================================
echo    My Tool - Kiem tra may  (khong sua gi, chi doc va in)
echo ============================================================
echo.
echo Thu muc tool: %~dp0
echo.

echo --- Python ---------------------------------------------------
where python 2>nul
where pythonw 2>nul
python --version 2>nul
echo.

echo --- Loi tat ngoai man hinh chinh ------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell;$p=Join-Path $w.SpecialFolders('Desktop') 'My Tool.lnk';if(Test-Path $p){$s=$w.CreateShortcut($p);Write-Host ('  target : ' + $s.TargetPath);Write-Host ('  args   : ' + $s.Arguments);Write-Host ('  workdir: ' + $s.WorkingDirectory)}else{Write-Host '  KHONG CO My Tool.lnk tren Desktop'}"
echo.

echo --- Claude Code CLI ------------------------------------------
where claude 2>nul
if exist "%USERPROFILE%\.local\bin\claude.exe" (
  echo   co file: %USERPROFILE%\.local\bin\claude.exe
) else (
  echo   KHONG thay %USERPROFILE%\.local\bin\claude.exe
)
REM Hoi PowerShell thay vi `find`: vai may co mot `find` khac cua Unix nam truoc
powershell -NoProfile -Command "if((($env:PATH -split ';') | Where-Object { $_ -like '*.local\bin*' })){Write-Host '  PATH co .local\bin: CO'}else{Write-Host '  PATH co .local\bin: KHONG  <-- extension se khong tim thay claude'}"
echo.

echo --- VS Code va extension -------------------------------------
set "CODE=%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"
if exist "%CODE%" (
  echo   co: %CODE%
  powershell -NoProfile -Command "$ds = & '%CODE%' --list-extensions 2>$null; if($ds -match 'anthropic.claude-code'){Write-Host '  extension anthropic.claude-code: DA CAI'}else{Write-Host '  extension anthropic.claude-code: CHUA CAI'}"
) else (
  where code 2>nul || echo   KHONG thay VS Code
)
echo.

echo --- Cau hinh Claude trong thu muc tool ------------------------
if exist "%~dp0.claude\settings.local.json" (
  echo   co file .claude\settings.local.json:
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$j=Get-Content -Raw '%~dp0.claude\settings.local.json' | ConvertFrom-Json;$e=$j.env;Write-Host ('    ANTHROPIC_BASE_URL   = ' + $e.ANTHROPIC_BASE_URL);$t=[string]$e.ANTHROPIC_AUTH_TOKEN;if($t){Write-Host ('    ANTHROPIC_AUTH_TOKEN = ' + $t.Substring(0,[Math]::Min(10,$t.Length)) + '... (' + $t.Length + ' ky tu)')}else{Write-Host '    ANTHROPIC_AUTH_TOKEN = (TRONG)'}}catch{Write-Host ('    doc khong duoc: ' + $_.Exception.Message)}"
) else (
  echo   CHUA co .claude\settings.local.json
  echo   ^(vao tab Agen xay tool, bam Mo VS Code mot lan la tool tu ghi^)
)
echo.
echo ============================================================
echo    Chup man hinh nay gui nguoi ho tro.
echo ============================================================
pause
