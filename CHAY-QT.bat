@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
title ShopAPI Studio (giao dien moi)
python -c "import PyQt5" 2>nul
if errorlevel 1 (
  echo Dang cai thu vien giao dien lan dau...
  python -m pip install --disable-pip-version-check PyQt5
)
python shopapi_studio_qt.py
if errorlevel 1 pause
