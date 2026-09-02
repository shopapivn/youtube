@echo off
REM MyTool VM - cai va mo tool cua kenh tren MAY AO. Xem vm/KE-HOACH.md.
REM File .bat phai thuan ASCII + CRLF (bai hoc 01/09 trong SETUP.bat).
chcp 65001 >nul
cd /d "%~dp0"
title MyTool VM
set "PY="
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if not defined PY (
  py -3 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  echo   !!! May ao chua co Python. Cai tu https://www.python.org/downloads/
  echo   ^(tich "Add python.exe to PATH"^) roi chay lai file nay.
  pause
  exit /b 1
)
echo   Kiem tra thu vien (lan dau hoi lau, cac lan sau vai giay)...
%PY% -m pip install -q -r requirements-vm.txt
%PY% cai_dat_vm.py
pause
