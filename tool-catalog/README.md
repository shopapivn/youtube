# Golden tool catalog

Day la bo manifest chuan dau tien cho pipeline YouTube cua ShopAPI Studio.
Moi thu muc chua mot `tool.json`; Studio chi nap metadata va kiem tra port, chua
tu dong cai dependency hay chay entrypoint khi doc catalog.

Pipeline mac dinh:

`research.youtube -> content.remake -> voice.shopapi -> transcribe.local -> prompt.workbook -> image.shopapi -> video.shopapi -> edit.ffmpeg`

`schema` la hop dong du lieu, con `kind` la nhom artifact de UI chon cach hien
thi. Cac permission duoc khai bao de runner xin phep nguoi dung truoc khi chay.
