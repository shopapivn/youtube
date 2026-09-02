@echo off
REM Cai agent len MAY AO - chep thu muc vm/ vao CANH Chrome cua kenh roi
REM nhay dup file nay. Khong phai go gi: tram tu do, kenh tu doan.
REM File .bat phai thuan ASCII + CRLF (bai hoc 01/09 trong SETUP.bat).
chcp 65001 >nul
cd /d "%~dp0"
title VM agent
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
%PY% cai_dat_vm.py
pause
