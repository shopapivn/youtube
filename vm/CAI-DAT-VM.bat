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

if exist "goi-vps\tool.zip" goto VPS

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
exit /b 0

:VPS
REM ===== goi-vps\tool.zip mang theo CA TOOL - cai_dat_vps.py lo tron ven =====
REM Khong pip-install gi o day: cai_dat_vps.py tu lo, ke ca requirements-vm.txt.
title MyTool VPS - cai dat
echo   Thay goi-vps\tool.zip - cai dat CHE DO VPS (ca tool, khong chi vm).
if defined PY goto CO_PYTHON

echo   May nay chua co Python - dang tai va cai ban chinh chu tu python.org
echo   (rieng cho tai khoan nay, khong can quyen quan tri, hoi lau lan dau)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $u='https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; $o=Join-Path $env:TEMP 'python-cai-vps.exe'; Invoke-WebRequest -Uri $u -OutFile $o -UseBasicParsing; Start-Process -FilePath $o -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=0','Include_launcher=0' -Wait"

python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if not defined PY (
  py -3 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
REM Cai per-user (PrependPath=0) khong dong PATH lai duoc trong cung phien
REM cmd nay, nen do thang duong da biet (ban 3.11 vua tai o tren).
REM LUAT DAT PY LA DUONG DAN: nhay phai nam TRONG gia tri (set PY="..."),
REM khong phai "set "PY=..."" - ten nguoi dung co dau cach se cat cut lenh.
if not defined PY if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
  set PY="%LocalAppData%\Programs\Python\Python311\python.exe"
)
if not defined PY (
  echo   !!! Khong tu cai duoc Python. Cai tay tu https://www.python.org/downloads/
  echo   roi chay lai file nay.
  pause
  exit /b 1
)

:CO_PYTHON
%PY% cai_dat_vps.py
pause
