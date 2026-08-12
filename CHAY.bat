@echo off
REM ===========================================================================
REM  File .bat PHAI thuan ASCII - xem loi giai thich o dau SETUP.bat.
REM ===========================================================================
REM  Khong dung "setlocal enabledelayedexpansion" - xem loi giai thich o SETUP.bat
REM  (bat len la cmd.exe an het dau cham than trong echo).
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
title ShopAPI Studio - Giong noi, Anh, Video

REM Dang chay tu ben trong file ZIP? Xem loi giai thich day du o SETUP.bat.
REM Neu de lot o day thi khach van dung duoc tool, nhung khoa API va thu muc
REM ket-qua nam trong thu muc tam cua Windows va se bien mat.
set "HERE=%~dp0"
echo "%HERE%" | find /i "\AppData\Local\Temp\" >nul
if not errorlevel 1 goto :in_zip
echo "%HERE%" | find /i "\Temp1_" >nul
if errorlevel 1 goto :place_ok

:in_zip
echo.
echo *** BAN DANG CHAY TOOL TU BEN TRONG FILE NEN (.zip) ***
echo.
echo   Ket qua va khoa API cua ban se bi Windows xoa mat.
echo   Hay giai nen ShopAPI-Studio.zip ra mot thu muc that, vi du C:\ShopAPI-Studio,
echo   roi mo CHAY.bat trong thu muc do.
echo.
pause
exit /b 1

:place_ok
REM Tim Python giong het SETUP.bat: thu "python", khong duoc thi thu "py".
REM Nho buoc nay, nguoi quen tich "Add Python to PATH" van chay duoc tool.
set "PYEXE="
python --version >nul 2>&1
if errorlevel 1 goto :try_py
REM Bo qua ban "python.exe" gia cua Microsoft Store - xem SETUP.bat.
python -c "import sys; print(sys.executable)" 2>nul | find /i "\WindowsApps\" >nul
if errorlevel 1 (
  set "PYEXE=python"
  goto :run
)

:try_py
py -3 --version >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=py -3"
  goto :run
)

echo.
echo *** CHUA CAI PYTHON ***
echo.
echo   Ban chua chay buoc cai dat. Hay:
echo     1^) Dong cua so nay.
echo     2^) Nhay dup file  SETUP.bat  ^(nam cung thu muc^).
echo     3^) Lam theo huong dan trong do, roi mo lai CHAY.bat.
echo.
pause
exit /b 1

:run
REM Chua cai thu vien thi shopapi_studio.py tu bao bang tieng Viet roi thoat 1.
%PYEXE% shopapi_studio.py
if errorlevel 1 (
  echo.
  echo *** TOOL DUNG DOT NGOT ***
  echo.
  echo   - Neu bao thieu thu vien: nhay dup SETUP.bat mot lan roi mo lai CHAY.bat.
  echo   - Neu bao loi khac: chup man hinh nay gui nguoi ho tro.
  echo     ^(Yen tam, API key cua ban khong bao gio bi ghi ra man hinh nay.^)
  echo.
  pause
)
