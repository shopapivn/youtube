@echo off
REM ===========================================================================
REM  QUAN TRONG CHO NGUOI SUA FILE NAY:
REM  File .bat PHAI la thuan ASCII, khong dau, khong ky tu ke khung.
REM  cmd.exe doc file batch theo tung byte va nho vi tri dang doc; mot ky tu
REM  nhieu byte (chu co dau, dau gach ke) se lam no doc lech va bam nat lenh.
REM  Chu tieng Viet co dau chi duoc nam trong file .py, khong nam o day.
REM ===========================================================================
REM  Va TUYET DOI khong dung "setlocal enabledelayedexpansion" o file nay:
REM  bat no len thi cmd.exe an het dau chAM than trong lenh echo, ma toan bo
REM  canh bao cua file nay danh dau bang "!!!". Da dinh mot lan: dong
REM  "CAI XONG!" in ra thanh "CAI XONG". Muon lay duong dan python thi dung
REM  ong dan (pipe) thang vao find, khong can bien trung gian.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
title My Tool - CAI DAT (chay 1 lan)
echo ============================================================
echo    My Tool - Cai dat cho may moi
echo ============================================================
echo.

REM --- [0/5] Dang chay TRONG file ZIP? --------------------------------------
REM Bay pho bien nhat va kho doan nhat. Nhay dup SETUP.bat ngay trong cua so
REM ZIP thi Windows giai nen len mot thu muc tam roi chay o do. Cai dat se
REM "thanh cong", nhung config.json, khoa API va toan bo thu muc ket-qua nam
REM trong thu muc tam do - Windows xoa luc nao khong bao. Khach se tuong tool
REM lam mat ket qua cua ho.
echo [0/5] Kiem tra vi tri thu muc...
REM Dat duong dan trong dau nhay khi day vao find: thu muc co the chua ky tu
REM "&" (vi du "C:\Tom & Jerry\") - khong nhay thi cmd hieu do la lenh moi.
set "HERE=%~dp0"
echo "%HERE%" | find /i "\AppData\Local\Temp\" >nul
if not errorlevel 1 goto :in_zip
echo "%HERE%" | find /i "\Temp1_" >nul
if not errorlevel 1 goto :in_zip
echo "%HERE%" | find /i "\INetCache\" >nul
if errorlevel 1 goto :place_ok

:in_zip
echo.
echo   !!! BAN DANG CHAY TOOL TU BEN TRONG FILE NEN (.zip).
echo.
echo   Thu muc hien tai la thu muc TAM cua Windows:
echo     %HERE%
echo   Windows se xoa no bat cu luc nao - keo theo khoa API va ket qua cua ban.
echo.
echo   Hay lam dung the nay:
echo     1^) Dong cua so nay lai.
echo     2^) Bam chuot phai vao file .zip vua tai ve, chon "Extract All"
echo        ^(hoac "Giai nen tat ca"^).
echo     3^) Chon mot cho de nho, vi du:   C:\My-Tool
echo     4^) Mo thu muc VUA GIAI NEN ra, roi nhay dup SETUP.bat trong do.
echo.
pause
exit /b 1

:place_ok
echo   - Vi tri OK: %HERE%
echo.

REM --- [1/5] Tim Python ------------------------------------------------------
REM Thu "python" truoc. Neu khong co, thu "py" - trinh khoi dong di kem moi ban
REM Python tren Windows. Rat nhieu nguoi quen tich "Add Python to PATH" luc cai;
REM khi do lenh "python" khong chay nhung "py" thi VAN CHAY. Do chinh la cho
REM 9/10 nguoi moi bi tac, nen tool tu do thay vi bat ho go lai tu dau.
echo [1/5] Kiem tra Python...
set "PYEXE="
python --version >nul 2>&1
if errorlevel 1 goto :try_py
REM Windows 10/11 co san mot "python.exe" GIA trong WindowsApps: bam vao la no
REM mo Microsoft Store chu khong chay gi. Ban gia nay doi khi van tra ve ma
REM thoat 0, nen phai hoi thang no dang nam o dau moi biet that hay gia.
python -c "import sys; print(sys.executable)" 2>nul | find /i "\WindowsApps\" >nul
if errorlevel 1 (
  set "PYEXE=python"
  goto :found
)
echo   - Lenh "python" dang tro vao ban gia cua Microsoft Store, bo qua.

:try_py
py -3 --version >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=py -3"
  echo   - Khong goi duoc lenh "python", nhung tim thay "py". Dung "py" cung duoc.
  goto :found
)

REM May Windows moi thuong co winget. Neu co, Studio tu cai Python chinh thuc
REM cho current user va tiep tuc ngay, khach khong phai mo web hay sua PATH.
where winget >nul 2>&1
if errorlevel 1 goto :python_tai_thang
echo.
echo   - May chua co Python. Studio se tu cai Python 3.12 chinh thuc...
winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :python_manual

REM Process cmd dang chay khong tu nhan PATH moi. Tim thang vi tri mac dinh cua
REM goi winget; py launcher la duong lui neu installer da dang ky no.
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
  goto :found
)
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=py -3.12"
  goto :found
)

REM -- Khong co winget: tai thang bo cai chinh thuc tu python.org ----------
REM
REM  Day la mat xich DAU TIEN cua ca chuoi. Hong o day thi khach chua kip nhin
REM  thay tool lan nao. Phan lon may khach la may Windows sach, va nhieu may
REM  chua co winget - dung nhung may can giup nhat.
REM
REM  Ban /quiet InstallAllUsers=0 cai vao thu muc nguoi dung: KHONG hoi quyen
REM  quan tri, khong dung Program Files. PrependPath=1 de lan sau go "python"
REM  la chay.
:python_tai_thang
echo.
echo   Khong co winget. Dang tai Python 3.12 tu python.org (~27 MB)...
set "PYSETUP=%TEMP%\shopapi-python-3.12.8.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$ProgressPreference='SilentlyContinue';Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%PYSETUP%' -UseBasicParsing}catch{exit 1}"
if errorlevel 1 goto :python_manual
if not exist "%PYSETUP%" goto :python_manual
echo   Dang cai Python (khong hoi gi them)...
"%PYSETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1
del /q "%PYSETUP%" >nul 2>&1
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
  goto :found
)
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=py -3.12"
  goto :found
)

:python_manual
echo.
echo   !!! CHUA THE TU CAI PYTHON.
echo.
echo   Windows nay khong co winget, hoac winget bi chan. Lam theo 3 buoc:
echo     1^) Mo https://www.python.org/downloads/
echo     2^) Tai Python va tich [v] Add python.exe to PATH.
echo     3^) Bam Install Now, roi chay lai SETUP.bat.
echo.
pause
exit /b 1

:found
%PYEXE% --version
%PYEXE% -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)"
if errorlevel 1 (
  echo.
  echo   !!! PYTHON QUA CU. Tool can Python 3.9 tro len.
  echo   -^> Tai ban moi tai https://www.python.org/downloads/
  echo      ^(nho tich "Add python.exe to PATH"^) roi chay lai SETUP.bat.
  echo.
  pause
  exit /b 1
)
echo.

REM --- [2/5] Bao dam co pip --------------------------------------------------
REM Vai ban Python rut gon ^(hoac cai qua Microsoft Store^) khong kem pip. Khong
REM co pip thi buoc sau that bai voi loi "No module named pip" - kho hieu voi
REM khach. ensurepip la do di kem Python, dung duoc khi khong co mang.
echo [2/5] Kiem tra pip...
%PYEXE% -m pip --version >nul 2>&1
if errorlevel 1 (
  echo   - Chua co pip, dang bat len bang ensurepip...
  %PYEXE% -m ensurepip --upgrade >nul 2>&1
  %PYEXE% -m pip --version >nul 2>&1
  if errorlevel 1 (
    echo.
    echo   !!! MAY BAN CO PYTHON NHUNG KHONG CO PIP.
    echo   -^> Cach chac an nhat: go Python hien tai di, cai lai ban tai tu
    echo      https://www.python.org/downloads/ ^(nho tich "Add python.exe to PATH"^).
    echo.
    pause
    exit /b 1
  )
)
REM Nang cap pip la viec NEN co, khong phai BAT BUOC. Ban pip cu van cai duoc
REM requirements.txt cua tool ^(file do da duoc giu thuan ASCII dung vi ly do
REM nay^), nen may khong co mang luc nay cung khong sao. Khong kiem errorlevel.
%PYEXE% -m pip install --upgrade pip -q --disable-pip-version-check 2>nul
echo   - pip: OK
echo.

REM --- [3/5] Thu vien --------------------------------------------------------
REM
REM  "-q" o day KHONG phai de cho dep. Khong co no, buoc nay do ra ~20 dong
REM  "Requirement already satisfied: ..." lan trong may dong "WARNING:" cua
REM  chinh may khach. Nguoi lam YouTube doc man hinh do se nghi tool bao loi,
REM  va nguoi doc man hinh do CHAM CHU nhat lai la nguoi dang lo lang nhat.
REM  "-q" van cho loi that di qua - no chi bo nhung dong "khong co gi de lam".
REM  Doi lai voi "-q": buoc nay im lang trong luc tai ~50 MB. Im lang lau la
REM  khach tuong may treo roi tat cua so giua chung. Nen phai noi truoc.
echo [3/5] Cai thu vien giao dien va ket noi...
echo   - Lan dau co the mat vai phut ^(dang tai ~50 MB^). Dung tat cua so nay.
%PYEXE% -m pip install -q -r requirements.txt --disable-pip-version-check
if errorlevel 1 (
  echo.
  echo   - Cai kieu thong thuong khong duoc. Thu cai rieng cho tai khoan cua ban...
  echo.
  REM Tren may cong ty / may cai Python cho "moi nguoi dung", thu muc thu vien
  REM nam trong Program Files va can quyen quan tri. "--user" ghi vao thu muc
  REM rieng cua khach nen khong can quyen gi ca. Thu cach nay TRUOC khi bat
  REM khach di tim nut "Run as administrator".
  %PYEXE% -m pip install -q -r requirements.txt --user --disable-pip-version-check
  if errorlevel 1 (
    echo.
    echo   !!! CAI THU VIEN THAT BAI.
    echo.
    echo   Thuong do mot trong ba ly do:
    echo     1^) May khong vao duoc mang / dang bi chan proxy.
    echo        -^> Thu mo trinh duyet vao https://pypi.org xem co vao duoc khong.
    echo     2^) Phan mem diet virus chan pip tai file.
    echo        -^> Tat tam thoi roi chay lai SETUP.bat.
    echo     3^) Thieu quyen ghi.
    echo        -^> Bam chuot phai vao SETUP.bat, chon "Run as administrator".
    echo.
    echo   Chup man hinh nay gui nguoi ho tro neu van khong duoc.
    echo.
    pause
    exit /b 1
  )
)
echo   - Thu vien: OK
echo.

REM --- [4/5] Kiem tra lai ----------------------------------------------------
echo [4/5] Kiem tra lai...
REM Do PyQt5, KHONG do tkinter. Buoc nay tung do "import tkinter" - ma tkinter
REM di kem san moi ban Python, nen no bao OK tren MOI may ke ca may chua he co
REM PyQt5. Mot buoc kiem luon luon dung la mot buoc kiem vo dung.
REM
REM  === VI SAO KHONG DUNG LAI O DAY KHI IMPORT HONG ===
REM
REM  pip bao "Thu vien: OK" o buoc [3/5] nghia la WHEEL da tai va giai nen xong
REM  - KHONG nghia la import duoc. PyQt5 la thu vien C: file .pyd cua no can
REM  ban chay Microsoft Visual C++ (vcruntime140.dll, msvcp140.dll). May
REM  Windows sach - dung may khach hay dung nhat - thuong CHUA co bo do, va khi
REM  do import chet voi:
REM
REM     ImportError: DLL load failed while importing QtWidgets:
REM     The specified module could not be found.
REM
REM  Loi nay khong nhac gi den "Visual C++" nen khach khong doan ra, va ban cu
REM  chi bao "chup man hinh gui ho tro" - be tac ngay o buoc dau, y het luc
REM  thieu Python. Nen o day tu tai va cai bo do (giong het cach tren da tu cai
REM  Python), roi thu import lai. Chi khi van hong moi bat khach lam thu cong.
%PYEXE% -c "import PyQt5.QtWidgets, PIL" 2>nul
if not errorlevel 1 goto :qt_ok

echo   - Giao dien chua mo duoc. Nhieu kha nang may thieu ban chay Microsoft
echo     Visual C++. Studio se tu tai va cai (~25 MB, khong hoi gi them)...

REM Chon dung ban x64 hay x86 theo chinh Python dang dung - khong theo Windows.
REM Python 32-bit tren Windows 64-bit thi phai lay ban x86, lay nham la vo ich.
set "VCARCH=x64"
for /f "delims=" %%i in ('%PYEXE% -c "import struct;print('x64' if struct.calcsize('P')==8 else 'x86')" 2^>nul') do set "VCARCH=%%i"

set "VCEXE=%TEMP%\shopapi-vc_redist.%VCARCH%.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$ProgressPreference='SilentlyContinue';Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vc_redist.%VCARCH%.exe' -OutFile '%VCEXE%' -UseBasicParsing}catch{exit 1}"
if errorlevel 1 goto :qt_bao_loi
if not exist "%VCEXE%" goto :qt_bao_loi
echo   - Dang cai ban chay Microsoft Visual C++...
REM /norestart: dung tu khoi dong lai may giua chung buoi cai cua khach. Ma
REM thoat 3010 nghia la "cai xong, can khoi dong lai" - van la thanh cong, nen
REM khong kiem errorlevel o day ma thu import lai lam thuoc do that su.
"%VCEXE%" /install /quiet /norestart
del /q "%VCEXE%" >nul 2>&1

%PYEXE% -c "import PyQt5.QtWidgets, PIL" 2>nul
if not errorlevel 1 goto :qt_ok

:qt_bao_loi
echo.
echo   !!! Chua mo duoc giao dien (PyQt5).
echo.
echo   Da cai ban chay Microsoft Visual C++ nhung van chua duoc. Thu:
echo     1^) Khoi dong lai may mot lan roi chay lai SETUP.bat
echo        ^(ban chay Visual C++ doi khi chi an sau khi khoi dong lai^).
echo     2^) Neu van khong duoc: chup man hinh nay gui nguoi ho tro.
echo.
pause
exit /b 1

:qt_ok
%PYEXE% -c "import PyQt5.QtWidgets, PIL; print('  - Giao dien Qt: OK')"
REM Do luon cac thu vien cua tab "Tu dong". Chung khong can de MO tool, nen
REM thieu chung thi buoc kiem cu van bao OK - roi khach bam Chay o tab Tu dong,
REM tool chay het ba khau dau (da TRA TIEN) moi chet o khau 4. Do o day thi
REM khach biet ngay luc cai, chua mat dong nao.
%PYEXE% -c "import openpyxl, faster_whisper, huggingface_hub, yaml; print('  - Tab Tu dong: OK')"
if errorlevel 1 (
  echo.
  echo   !!! Thieu thu vien cho tab Tu dong.
  echo   -^> Chay lai SETUP.bat khi may co mang. Cac tab khac van dung duoc.
  echo.
)
REM FFmpeg: can cho khau dung video va khau tach phu de. Uu tien ban cai san
REM tren may; khong co thi lay ban di kem imageio-ffmpeg.
%PYEXE% -c "import sys, os; sys.path.insert(0, os.getcwd()); from core.dung_video import tim_ffmpeg; p = tim_ffmpeg(); print('  - FFmpeg:', p or 'KHONG THAY'); sys.exit(0 if p else 1)"
if errorlevel 1 (
  echo.
  echo   !!! Khong tim thay FFmpeg. Khau dung video se khong chay duoc.
  echo   -^> Chay lai SETUP.bat khi may co mang de cai imageio-ffmpeg.
  echo.
)
REM Nhap "core" truoc: chinh no lo viec tim SDK. SDK shopapi CHUA len PyPI nen
REM khong cai bang pip duoc - ban tai ve kem san SDK trong thu muc _sdk\, va
REM core\__init__.py biet duong tim o do. Chay trong ma nguon du an thi no lay
REM o packages\sdk-python\src. Ca hai deu khong can mang.
%PYEXE% -c "import sys, os; sys.path.insert(0, os.getcwd()); import core, shopapi; print('  - SDK shopapi:', shopapi.__version__)"
if errorlevel 1 (
  echo.
  echo   !!! KHONG TIM THAY SDK shopapi.
  echo.
  echo   Thu muc _sdk phai nam ngay canh file SETUP.bat nay. Kha nang cao la
  echo   luc giai nen bi thieu file. Hay xoa thu muc nay di, giai nen lai
  echo   ShopAPI-Studio.zip mot lan nua cho day du, roi chay lai SETUP.bat.
  echo.
  pause
  exit /b 1
)
REM yt-dlp chi phuc vu tab Nghien cuu doi thu (mien phi, chay tren may khach).
REM Thieu no thi ca tool VAN CHAY, nen o day chi nhac chu khong dung setup lai.
%PYEXE% -c "import yt_dlp; print('  - yt-dlp:', yt_dlp.version.__version__)"
if errorlevel 1 (
  echo   - Chua co yt-dlp. Tab Nghien cuu doi thu se moi ban cai bang 1 nut bam.
)
echo.

REM --- [5/5] Thu mo tool that ------------------------------------------------
REM Import duoc thu vien KHONG co nghia la tool mo duoc cua so. Buoc nay nap
REM dung man hinh chinh (khong hien ra) de bat loi ngay bay gio, luc man hinh
REM con dang huong dan, thay vi de khach gap luc nhay dup CHAY-GON.vbs.
echo [5/5] Thu nap giao dien...
%PYEXE% -c "import sys, os; sys.path.insert(0, os.getcwd()); import core; from ui_qt.app import CuaSoChinh; print('  - Giao dien nap duoc: OK')"
if errorlevel 1 (
  echo.
  echo   !!! Thu vien da cai xong nhung giao dien khong nap duoc.
  echo   -^> Chup man hinh nay gui nguoi ho tro, kem dong loi mau do o tren.
  echo.
  pause
  exit /b 1
)
echo.

REM --- Loi tat ngoai man hinh chinh -----------------------------------------
REM
REM  Khong bat buoc, nen HONG O DAY THI KE. Thieu loi tat thi khach van nhay
REM  dup CHAY-GON.vbs trong thu muc tool duoc; chan ca buoc cai vi mot cai
REM  shortcut la doi mot thu tien nghi lay mot thu thiet yeu.
REM
REM  Vi sao dang lam: file .vbs khong mang icon rieng duoc, no luon deo icon
REM  cua VBScript. Chi loi tat (.lnk) moi tro duoc IconLocation vao logo.ico,
REM  nen day la cho DUY NHAT khach nhin thay logo truoc khi tool mo len.
REM
REM  === LOI TAT TRO THANG pythonw.exe, KHONG QUA wscript, KHONG QUA .vbs ===
REM
REM  Ba doi cua cho nay, va vi sao doi:
REM
REM   1. Tro vao CHAY-GON.vbs.  Windows mo .vbs bang chuong trinh dang GIU duoi
REM      .vbs. Tab Agent cua tool co cai VS Code, va ban cai tung mang co
REM      "associatewithfiles" - VS Code gianh ca .vbs. May da bi gianh thi nhay
REM      dup loi tat khong chay tool nua ma MO MA NGUON trong trinh soan thao.
REM   2. Tro vao wscript.exe, dua .vbs lam tham so.  Het phu thuoc lien ket
REM      file, nhung VAN con wscript va van con .vbs trong day chuyen - hai mat
REM      xich nua co the hong tren may khach ma minh khong nhin thay.
REM   3. (nay) Tro thang pythonw.exe, dua shopapi_studio_qt.py lam tham so.
REM
REM  Doi lan 3 vi mot bang chung chu khong phai vi mot linh cam: tren may chu
REM  du an co san hai loi tat tool khac - CONTENT.lnk va VOICE.lnk - ca hai deu
REM  tro thang pythonw.exe kem mot file .py, va ca hai deu chay duoc. Do la
REM  cach ngan nhat: khong script host, khong lien ket file, khong gi de gianh.
REM
REM  Duong pythonw lay tu chinh Python vua dung o cac buoc tren (%PYEXE%), nen
REM  loi tat chac chan dung ban Python da cai thu vien - khong phai ban nao do
REM  lan trong PATH.
REM
REM  [char]34 la dau nhay kep - dung no de khoi long nhay trong nhay giua cmd
REM  va powershell. Duong dan co dau cach ("C:\Users\A Plus Computer\...") nen
REM  tham so bat buoc phai duoc boc nhay.
echo Dang tao loi tat "My Tool" ngoai man hinh chinh...
set "PYW="
for /f "delims=" %%i in ('%PYEXE% -c "import os,sys;d=os.path.dirname(sys.executable);p=os.path.join(d,'pythonw.exe');print(p if os.path.isfile(p) else '')" 2^>nul') do set "PYW=%%i"
if not defined PYW (
  REM Khong tim ra pythonw thi lui ve duong cu. Ban Python rut gon co the
  REM khong kem pythonw.exe; luc do wscript+vbs van hon la khong co loi tat.
  set "PYW=%SystemRoot%\System32\wscript.exe"
  set "PYARG=%~dp0CHAY-GON.vbs"
) else (
  set "PYARG=%~dp0shopapi_studio_qt.py"
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$q=[char]34;$g='%~dp0'.TrimEnd('\');$w=New-Object -ComObject WScript.Shell;$p=Join-Path $w.SpecialFolders('Desktop') 'My Tool.lnk';$s=$w.CreateShortcut($p);$s.TargetPath='%PYW%';$s.Arguments=$q+'%PYARG%'+$q;$s.WorkingDirectory=$g;$s.IconLocation=(Join-Path $g 'ui_qt\logo.ico');$s.Description='My Tool';$s.Save();Write-Host ('  - Da tao loi tat tren Desktop -> ' + (Split-Path $s.TargetPath -Leaf))}catch{Write-Host '  - Chua tao duoc loi tat (khong sao, nhay dup CHAY-QT.bat trong thu muc nay)'}"
echo.

REM --- Mo tool luon ---------------------------------------------------------
REM
REM  === MOT MAN HINH, MOT VIEC ===
REM
REM  Ban truoc man hinh nay dua ra BON loi vao: loi tat, CHAY-GON.vbs,
REM  CHAY-QT.bat, roi lai dan "tu gio ban CHI CAN nhay dup CHAY-GON.vbs" -
REM  mau thuan voi dong dau bao dung loi tat. Nguoi biet viec doc thay day du;
REM  nguoi khong biet viec doc thay bon nga re va khong biet re dau.
REM
REM  Nay chi con MOT viec, va dung cai viec do SETUP tu lam ho luon: mo tool
REM  ra. Chay xong la khach dang NHIN THAY tool, khong phai dang doc huong dan
REM  ve cach mo tool. Ba loi vao kia van con nguyen trong thu muc, chi khong
REM  bat khach phai chon giua chung ngay bay gio.
REM
REM  "start" de SETUP thoat duoc ngay, khong nam giu cua so den suot phien
REM  lam viec cua khach. Dau nhay rong sau "start" la TEN CUA SO - thieu no
REM  thi cmd hieu duong dan la ten cua so va khong chay gi ca.
REM  Mo bang DUNG thu ma loi tat se chay (%PYW% + %PYARG%, dat o buoc tren).
REM  Neu hai duong khac nhau thi lan mo dau tien thanh cong khong chung minh
REM  duoc gi ve lan nhay dup ngay mai - ma lan nhay dup ngay mai moi la lan
REM  quan trong.
echo Dang mo tool...
start "" "%PYW%" "%PYARG%"
echo.

echo ============================================================
echo    XONG! Tool dang mo ra.
echo.
echo    Con MOT viec nua, lam ngay trong tool:
echo      Dang nhap bang email tai khoan shopapi.vn
echo      ^(tool tu tao khoa API va cat ma hoa tren may ban^)
echo.
echo    Chua co tai khoan? Dang ky mien phi:  https://shopapi.vn/register
echo.
echo    Lan sau mo tool: nhay dup bieu tuong  My Tool  ngoai man hinh chinh.
echo    Khong phai chay lai SETUP.bat nua.
echo ============================================================
echo.
echo    (Neu tool khong hien ra: nhay dup CHAY-QT.bat trong thu muc nay,
echo     no mo cua so den va noi ro dang thieu gi.)
pause
