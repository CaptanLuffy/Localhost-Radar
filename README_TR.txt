LOCALHOST RADAR v0.3.0 — BUILD 2026-08-30-B

1) Bu ZIP'i ESKI klasorun ustune cikarma.
   Yeni, ayri bir klasore tamamen cikart.

2) Ilk kez gerekiyorsa KUR.bat calistir.

3) Normal kullanimda:
   RUN_THIS_Localhost_Radar_v0.3.pyw
   dosyasina cift tikla.

SESSIZ MOD
- .pyw dosyasi pythonw.exe ile acilir.
- CMD / PowerShell penceresi acik kalmaz.
- Servis kurulmaz.
- Tray agent kurulmaz.
- Tarama ayri bir program/process degildir; GUI process'i icindeki QThread'dir.
- Pencere kapandiginda uygulama kapanir.

v0.3'TE GOZLE GORULUR FARKLAR
- Eski ust menu/toolbar yok.
- Ustte BUYUK Scan now, Full refresh ve Settings butonlari var.
- Ust baslikta v0.3.0 • BUILD 2026-08-30-B yaziyor.
- Tarama sirasinda READY -> SCANNING... degisiyor.
- Status bar Scan #1, Scan #2... diye artiyor ve son tarama saati degisiyor.
- Sag panel compact iki sutunlu duzende; Executable ve Command line ayri metin kutularinda.
- IPv4/IPv6 duplicate listener birlestirme varsayilan acik.
- PostgreSQL/MySQL gibi web olmayan servisler icin sahte http:// URL uretmiyor.

SCAN NOW
- Yeni net_connections taramasi yapar.
- Process bilgisi kisa cache'den gelebilir.

FULL REFRESH
- Process cache'i temizler.
- Ardindan tum listener'lari yeniden tarar.

Bir butonun calistigini anlamak icin:
- READY etiketi SCANNING... olur.
- Butonlar tarama boyunca pasif olur.
- Bitince Scan # sayaci ve Last scan saati degisir.
