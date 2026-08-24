@echo off
REM ===========================================================================
REM  File .bat PHAI thuan ASCII - xem ghi chu dau SETUP.bat.
REM ===========================================================================
REM
REM  === VI SAO KHONG GOI THANG "python" NUA ===
REM
REM  Ngay 24/08/2026 mot may khach dang chay tot, qua dem tu nhien khong mo
REM  duoc tool. Cua so den in ra:
REM
REM     Python was not found; run without arguments to install from the
REM     Microsoft Store, or disable this shortcut from Settings > Apps >
REM     Advanced app settings > App execution aliases.
REM
REM  Do la ban GIA cua Microsoft Store: Windows co san mot "python.exe" trong
REM  WindowsApps, bam vao no chi mo Store chu khong chay gi. Binh thuong no nam
REM  sau Python that trong PATH; nhung mot ban cap nhat Windows (hoac lan bat
REM  lai "App execution aliases") day no len truoc, the la "python" tro vao ban
REM  gia va ca tool chet - du Python that van con nguyen tren may.
REM
REM  Nen file nay KHONG goi "python" tay khong nua. No di tim ban Python THAT
REM  o dung cho da cai, bo qua ban gia WindowsApps.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
title My Tool (cua so den de xem loi)

REM --- Tim Python THAT (khong phai ban gia Microsoft Store) ------------------
set "PYEXE="

REM 1) Moi truong ao cua tool (neu co) - dung dung bo thu vien SETUP da cai.
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE if exist "%~dp0venv\Scripts\python.exe" set "PYEXE=%~dp0venv\Scripts\python.exe"

REM 2) Python Install Manager (Python 3.14+): %LocalAppData%\Python\pythoncore-*
if not defined PYEXE for /d %%d in ("%LocalAppData%\Python\pythoncore-*") do if not defined PYEXE if exist "%%d\python.exe" set "PYEXE=%%d\python.exe"

REM 3) Ban cai thong thuong cho current user: %LocalAppData%\Programs\Python\Python3*
if not defined PYEXE for /d %%d in ("%LocalAppData%\Programs\Python\Python3*") do if not defined PYEXE if exist "%%d\python.exe" set "PYEXE=%%d\python.exe"

REM 4) Lenh "python" trong PATH - CHI dung neu KHONG phai ban gia WindowsApps.
if defined PYEXE goto :co_python
python -c "import sys" >nul 2>&1
if errorlevel 1 goto :thu_py
python -c "import sys; print(sys.executable)" 2>nul | find /i "\WindowsApps\" >nul
if errorlevel 1 (
  set "PYEXE=python"
  goto :co_python
)

:thu_py
REM 5) Trinh khoi dong "py" - thuong van chay du "python" bi ban gia che.
if defined PYEXE goto :co_python
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3"

:co_python
if not defined PYEXE (
  echo.
  echo   !!! KHONG TIM THAY PYTHON THAT.
  echo.
  echo   Lenh "python" dang tro vao ban gia cua Microsoft Store
  echo   ^("Python was not found..."^) chu khong phai Python that.
  echo.
  echo   Cach sua nhanh nhat:
  echo     -^) Nhay dup SETUP.bat trong thu muc nay mot lan. No tu tim lai
  echo        Python that, tao lai loi tat va mo tool.
  echo.
  echo   Hoac tu tay tat ban gia:
  echo     -^) Mo Settings ^> Apps ^> Advanced app settings ^> App execution aliases
  echo        roi TAT hai dong "python.exe" va "python3.exe", sau do mo lai tool.
  echo.
  pause
  exit /b 1
)

echo Dung Python: %PYEXE%
%PYEXE% -c "import PyQt5" 2>nul
if errorlevel 1 (
  echo Dang cai thu vien giao dien lan dau...
  %PYEXE% -m pip install --disable-pip-version-check PyQt5
)
%PYEXE% shopapi_studio_qt.py
if errorlevel 1 pause
