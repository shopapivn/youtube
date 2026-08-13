' ===========================================================================
'  ShopAPI Studio — BẬT KHÔNG CÓ CỬA SỔ ĐEN
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

' ── Tìm pythonw.exe ────────────────────────────────────────────────────────
'
' `pythonw.exe` là bản Python KHÔNG mở console — khác đúng một chữ so với
' `python.exe`, và đó là toàn bộ điểm của file này.
'
' Thứ tự tìm giống SETUP.bat: môi trường ảo của tool trước, rồi mới tới Python
' của máy. Môi trường ảo trước là để tool luôn chạy bằng đúng bộ thư viện mà
' SETUP.bat đã cài, không phải bộ nào đó cài lẫn ở ngoài.
pythonw = ""

If fso.FileExists(thuMuc & "\.venv\Scripts\pythonw.exe") Then
    pythonw = thuMuc & "\.venv\Scripts\pythonw.exe"
ElseIf fso.FileExists(thuMuc & "\venv\Scripts\pythonw.exe") Then
    pythonw = thuMuc & "\venv\Scripts\pythonw.exe"
Else
    ' Không có môi trường ảo: nhờ `where` tìm trong PATH.
    Dim chay, dong
    On Error Resume Next
    Set chay = shell.Exec("cmd /c where pythonw.exe")
    If Err.Number = 0 Then
        Do While Not chay.StdOut.AtEndOfStream
            dong = Trim(chay.StdOut.ReadLine())
            If pythonw = "" And dong <> "" Then pythonw = dong
        Loop
    End If
    On Error GoTo 0
End If

If pythonw = "" Then
    MsgBox _
        "Không tìm thấy pythonw.exe." & vbCrLf & vbCrLf & _
        "Bạn nhấp đúp SETUP.bat một lần để cài Python và thư viện, rồi mở lại file này." & vbCrLf & vbCrLf & _
        "Nếu đã cài rồi mà vẫn báo lỗi này thì mở CHAY-QT.bat — nó hiện cửa sổ đen và " & _
        "nói rõ hơn đang thiếu gì.", _
        vbCritical, "ShopAPI Studio"
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
    MsgBox chiTiet, vbCritical, "ShopAPI Studio"
    WScript.Quit ma
End If
