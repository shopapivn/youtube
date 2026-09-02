' Mo MyTool VM ngam - khong cua so den. Loi tat ngoai man hinh va trong
' thu muc Khoi dong deu tro vao day; file nay goi CAI-DAT-VM.bat (no biet
' tu tim Python, tu cai thu vien, roi mo bang dieu khien).
' Chuoi VBScript: dau nhay trong chuoi phai GO DOI (""), va 02/09/2026
' da hong that vi thua mot dau nhay - sua gi o day thi chay thu:
'   cscript //nologo CHAY-NGAM.vbs
Set fso = CreateObject("Scripting.FileSystemObject")
goc = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = goc
lenh = Chr(34) & goc & "\CAI-DAT-VM.bat" & Chr(34)
sh.Run lenh, 0, False
