' ===========================================================================
'  My Tool — BẬT KHÔNG CÓ CỬA SỔ ĐEN
' ===========================================================================
'
'  Nhấp đúp file này thay cho CHAY-QT.bat. Không hiện cửa sổ dòng lệnh nào.
'
'  ── Vì sao có file này ─────────────────────────────────────────────────────
'
'  CHAY-QT.bat chạy `python.exe`, mà `python.exe` luôn kéo theo một cửa sổ đen.
'  Cửa sổ đó có ích lúc gỡ lỗi, nhưng với người dùng hằng ngày thì nó chỉ là
'  một ô đen nằm chình ình và bấm nhầm vào là tắt cả tool.
'
'  ── Vì sao KHÔNG xoá CHAY-QT.bat ───────────────────────────────────────────
'
'  Giữ cả hai là cố ý:
'
'      CHAY-GON.vbs  → dùng hằng ngày, không cửa sổ
'      CHAY-QT.bat   → khi có trục trặc, xem thẳng thông báo trong cửa sổ đen
'
'  Bỏ hẳn CHAY-QT.bat thì lúc hỏng sẽ không còn cách nào nhìn thấy lỗi.
'
'  ── Lỗi thì biết bằng cách nào khi không có cửa sổ ────────────────────────
'
'  `shopapi_studio_qt.py::_die` tự nhận ra mình chạy không console và bật một
'  hộp thoại thay vì in ra màn hình. Dựng cả hộp thoại cũng không nổi thì nó ghi
'  `LOI-KHOI-DONG.txt` ngay cạnh file này.
'
'  Riêng trường hợp KHÔNG TÌM THẤY Python thì `_die` chưa kịp chạy, nên chính
'  file này phải tự báo — xem khối cuối.
' ===========================================================================

Option Explicit

Dim fso, shell, thuMuc, pythonw, lenh
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

thuMuc = fso.GetParentFolderName(WScript.ScriptFullName)

' Giữ locale/múi giờ nhất quán cho mọi engine và Chrome con do Studio mở.
' IP mạng trực tiếp ở Việt Nam -> UTC+7, tiếng Việt. Các engine vẫn có thể
' đọc riêng VEO3TOP_TZ/VEO3TOP_LOCALE; TZ/LANG là giá trị chung cho tiến trình con.
shell.Environment("PROCESS")("TZ") = "Asia/Ho_Chi_Minh"
shell.Environment("PROCESS")("LANG") = "vi_VN.UTF-8"
shell.Environment("PROCESS")("LANGUAGE") = "vi_VN:vi"
shell.Environment("PROCESS")("VEO3TOP_TZ") = "Asia/Ho_Chi_Minh"
shell.Environment("PROCESS")("VEO3TOP_LOCALE") = "vi-VN"

' ── Tìm pythonw.exe THẬT (không phải bản giả Microsoft Store) ───────────────
'
' `pythonw.exe` là bản Python KHÔNG mở console — khác đúng một chữ so với
' `python.exe`, và đó là toàn bộ điểm của file này.
'
' 24/08/2026: một máy khách đang chạy tốt, qua đêm mở không lên. Nguyên do là
' `python`/`pythonw` trong PATH bị bản GIẢ trong WindowsApps che mất (một bản
' cập nhật Windows bật lại "App execution aliases", đẩy bản giả lên trước). Nên
' KHÔNG dựa vào PATH nữa: tìm thẳng ở đúng chỗ Python đã cài, và bỏ qua mọi thứ
' nằm trong WindowsApps. Môi trường ảo của tool được ưu tiên trước để chạy đúng
' bộ thư viện SETUP.bat đã cài, không phải bộ nào đó cài lẫn ở ngoài.
Dim lad
lad = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
pythonw = ""

' 1) Môi trường ảo của tool (nếu có).
If fso.FileExists(thuMuc & "\.venv\Scripts\pythonw.exe") Then
    pythonw = thuMuc & "\.venv\Scripts\pythonw.exe"
ElseIf fso.FileExists(thuMuc & "\venv\Scripts\pythonw.exe") Then
    pythonw = thuMuc & "\venv\Scripts\pythonw.exe"
End If

' 2) Python Install Manager (Python 3.14+): %LOCALAPPDATA%\Python\pythoncore-*
If pythonw = "" Then pythonw = TimTrongThuMuc(fso, lad & "\Python", "pythoncore-", "pythonw.exe")
' 3) Bản cài thông thường cho current user: %LOCALAPPDATA%\Programs\Python\Python3*
If pythonw = "" Then pythonw = TimTrongThuMuc(fso, lad & "\Programs\Python", "Python3", "pythonw.exe")

' 4) Nhờ `where` tìm trong PATH — nhưng BỎ bản giả nằm trong WindowsApps.
If pythonw = "" Then
    Dim chay, dong
    On Error Resume Next
    Set chay = shell.Exec("cmd /c where pythonw.exe")
    If Err.Number = 0 Then
        Do While Not chay.StdOut.AtEndOfStream
            dong = Trim(chay.StdOut.ReadLine())
            If pythonw = "" And dong <> "" And InStr(LCase(dong), "windowsapps") = 0 Then
                pythonw = dong
            End If
        Loop
    End If
    On Error GoTo 0
End If

' 5) Chỉ có python.exe (bản gọn không kèm pythonw): vẫn mở được, chỉ thoáng một
'    ô đen — còn hơn không mở được gì.
If pythonw = "" Then pythonw = TimTrongThuMuc(fso, lad & "\Python", "pythoncore-", "python.exe")
If pythonw = "" Then pythonw = TimTrongThuMuc(fso, lad & "\Programs\Python", "Python3", "python.exe")

If pythonw = "" Then
    MsgBox _
        "Không tìm thấy Python trên máy." & vbCrLf & vbCrLf & _
        "Thường gặp nhất: lệnh ""python"" đang trỏ vào bản GIẢ của Microsoft " & _
        "Store (báo ""Python was not found...""), không phải Python thật — hay " & _
        "xảy ra sau một bản cập nhật Windows." & vbCrLf & vbCrLf & _
        "Cách sửa nhanh: nhấp đúp SETUP.bat một lần. Nó tự tìm lại Python thật, " & _
        "tạo lại lối tắt và mở tool." & vbCrLf & vbCrLf & _
        "Nếu vẫn lỗi, mở CHAY-QT.bat — nó hiện cửa sổ đen và nói rõ đang thiếu gì.", _
        vbCritical, "My Tool"
    WScript.Quit 1
End If

' ── Bật tool ───────────────────────────────────────────────────────────────
'
' Tham số thứ hai `0` = cửa sổ ẩn hoàn toàn.
' Tham số thứ ba `True` = CHỜ tool thoát rồi mới đọc mã trả về.
'
' Vì sao chờ, dù script này trước đây thả tay ra là biến mất: chạy ẩn mà không
' chờ thì tool chết lúc khởi động là khách **không nhận được tín hiệu nào** —
' nhấp đúp, màn hình không đổi, không biết mình đã bấm đúng chưa nên bấm thêm
' vài lần nữa. Chờ thì tốn một tiến trình wscript.exe vô hình nằm không suốt
' phiên làm việc; đổi lại, mọi kiểu chết lúc khởi động đều nói được thành lời.
'
' Bọc đường dẫn trong dấu nháy: thư mục của tool có thể chứa khoảng trắng
' (mặc định nằm trong "D:\New folder\...").
Dim tepLoi, ma, chiTiet
tepLoi = thuMuc & "\LOI-KHOI-DONG.txt"
' Xoá manh mối của lần chạy TRƯỚC, không thì lát nữa đọc nhầm lỗi cũ.
If fso.FileExists(tepLoi) Then fso.DeleteFile tepLoi, True

lenh = """" & pythonw & """ """ & thuMuc & "\shopapi_studio_qt.py"""
shell.CurrentDirectory = thuMuc
ma = shell.Run(lenh, 0, True)

If ma <> 0 Then
    chiTiet = ""
    If fso.FileExists(tepLoi) Then
        On Error Resume Next
        chiTiet = fso.OpenTextFile(tepLoi, 1).ReadAll()
        On Error GoTo 0
    End If
    If Trim(chiTiet) = "" Then
        chiTiet = "Tool đóng lại ngay khi vừa mở (mã " & ma & ")." & vbCrLf & vbCrLf & _
                  "Hãy nhấp đúp CHAY-QT.bat — nó hiện cửa sổ đen và nói rõ đang thiếu gì."
    End If
    MsgBox chiTiet, vbCritical, "My Tool"
    WScript.Quit ma
End If

' ── TimTrongThuMuc ─────────────────────────────────────────────────────────
'
' Quét các thư mục con của `cha` có tên bắt đầu bằng `tienTo`, trả về đường dẫn
' tới `exe` trong thư mục con ĐẦU TIÊN chứa nó (hoặc "" nếu không có). Dùng để
' tìm Python ở đúng chỗ đã cài mà không cần biết số phiên bản (Python311,
' pythoncore-3.14-64, …).
Function TimTrongThuMuc(fso, cha, tienTo, exe)
    TimTrongThuMuc = ""
    If Not fso.FolderExists(cha) Then Exit Function
    Dim con, duong
    For Each con In fso.GetFolder(cha).SubFolders
        If LCase(Left(con.Name, Len(tienTo))) = LCase(tienTo) Then
            duong = con.Path & "\" & exe
            If fso.FileExists(duong) Then
                TimTrongThuMuc = duong
                Exit Function
            End If
        End If
    Next
End Function
