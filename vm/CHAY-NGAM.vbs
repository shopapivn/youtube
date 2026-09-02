' Chay agent VM ngam - khong cua so den. May ao bat len la file nay duoc
' goi tu thu muc Khoi dong (cai_dat_vm.dang_ky_tu_chay ghi vao do).
' Dung lai CAI-DAT-VM.bat: no biet tu tim Python; config co roi thi vao
' thang agent, agent moi tu don agent cu (mot_minh) nen bam may lan cung
' chi con dung MOT agent chay.
Set fso = CreateObject("Scripting.FileSystemObject")
goc = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = goc
sh.Run """" & goc & "\CAI-DAT-VM.bat"""", 0, False
