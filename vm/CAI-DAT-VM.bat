@echo off
REM Cai dat agent len MAY AO cua kenh - chay MOT lan. Xem vm/KE-HOACH.md.
REM File .bat phai thuan ASCII + CRLF (bai hoc 01/09 trong SETUP.bat cua tool).
chcp 65001 >nul
cd /d "%~dp0"
title Cai dat VM agent
echo ============================================================
echo    Cai dat agent cua kenh len may ao nay
echo ============================================================
echo.

REM --- Python co chua ---------------------------------------------------------
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
%PY% --version

REM --- Da co config thi thoi, chi chay ---------------------------------------
if exist config.json (
  echo   - Da co config.json, dung nguyen. Muon dat lai thi xoa no di.
  goto :chay
)

REM --- Hoi ba cau roi tu viet config -----------------------------------------
echo.
echo Ba cau hoi ^(dan bang chuot phai trong cua so nay^):
echo.
set /p TRAM="1) Dia chi tram (lay o muc Chi so kenh sau khi Bat cong nhan): "
set /p KENH="2) Ma kenh (dung ten thu muc trong CHANNEL, vd TL4-T7): "
set /p CHROME="3) Duong Chrome cua kenh (Enter de dien sau vao config.json): "
%PY% -c "import json,os;json.dump({'tram':os.environ.get('TRAM',''),'kenh':os.environ.get('KENH',''),'ten_may':os.environ.get('COMPUTERNAME','vm'),'chrome':os.environ.get('CHROME',''),'studio_url':'https://studio.youtube.com','cho_quet_giay':480,'cho_trang_chu_giay':90,'dong_chrome_sau_quet':False,'gio_quet':'07:30','quet_trang_chu_hang_ngay':True,'tool_dang':''},open('config.json','w',encoding='utf-8'),ensure_ascii=False,indent=4)"
if not exist config.json (
  echo   !!! Chua viet duoc config.json - chep tay tu config.example.json.
  pause
  exit /b 1
)
echo   - Da viet config.json ^(gio quet hang ngay: 07:30 - sua duoc trong file^).
echo.

:chay
echo Dang chay agent... Tren tool: Phan tich ^& Nghien cuu ^> May VM se thay
echo may nay len tieng trong vong nua phut.
echo.
%PY% agent.py
pause
