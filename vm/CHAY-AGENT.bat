@echo off
REM Chay agent cua kenh tren MAY AO. Xem vm/KE-HOACH.md.
REM File .bat phai thuan ASCII + CRLF - xem chu thich dau SETUP.bat cua tool.
cd /d "%~dp0"
title VM agent - hoi viec tu tram cua tool
if not exist config.json (
  echo Chua co config.json - chep config.example.json thanh config.json roi
  echo dien: dia chi tram, ma kenh, duong Chrome cua kenh.
  pause
  exit /b 1
)
python agent.py
pause
