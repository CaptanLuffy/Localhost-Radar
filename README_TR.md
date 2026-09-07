<div align="center">

# Localhost Radar

**Bilgisayarında hangi yerel portun hangi süreç tarafından kullanıldığını gösteren hafif Windows masaüstü aracı.**

`v0.3.0` · `BUILD 2026-08-30-B`

[English README](README.md)

</div>

Localhost Radar, dinleyen TCP portlarını tarar, portları ilgili süreçlerle eşleştirir ve sonucu kompakt bir masaüstü arayüzünde gösterir. Özellikle yerel geliştirme ve sorun giderme için tasarlanmıştır: unutulmuş geliştirme sunucularını bulmak, bir portu hangi sürecin kullandığını görmek, web servisi olduğu düşünülen uç noktaları tarayıcıda açmak ve gerektiğinde normal süreçleri güvenli biçimde sonlandırmak.

## Öne çıkan özellikler

- Gerçek **Scan now** ve **Full refresh** işlemleri
- Tarama sırasında görünür durum değişimi, tarama sayacı ve son tarama zamanı
- PID, süreç adı, executable yolu, command line, kullanıcı ve başlangıç zamanı
- Yalnızca web servisi olduğu düşünülen portlarda **Open in browser**
- IPv4 / IPv6 çift listener kayıtlarını birleştirme
- Favoriler ve filtreleme
- Muhtemel unutulmuş geliştirme sunucusu uyarısı
- Kritik Windows süreçlerinde **End process** koruması
- Ayarların kullanıcı uygulama-verisi klasöründe kalıcı tutulması
- Sessiz `.pyw` başlatıcı: açık CMD / PowerShell penceresi yok
- Ayrı servis, tray agent veya ikinci uzun süre çalışan backend process yok
- Tarama aynı GUI process'i içindeki `QThread` üzerinde çalışır

## Gereksinimler

- Windows 10 / 11
- Python 3.10+ önerilir
- PySide6
- psutil

## Kurulum ve çalıştırma

1. Repoyu indir veya clone et.
2. İlk kullanımda `KUR.bat` dosyasını çalıştır.
3. Normal kullanım için `RUN_THIS_Localhost_Radar_v0.3.pyw` dosyasına çift tıkla.

Hata ayıklama çıktısı görmek için `BASLAT_DEBUG.bat` kullanılabilir.

Doğru sürüm açıldığında pencere başlığında ve üst bölümde şu bilgi görünmelidir:

```text
v0.3.0 • BUILD 2026-08-30-B
```

Bu metin görünmüyorsa eski bir Localhost Radar kopyası açılıyor olabilir.

## Butonlar

### Scan now

Yeni bir `psutil.net_connections()` taraması yapar. Süreç bilgileri kısa süreli process cache'inden gelebilir.

### Full refresh

Önce process cache'ini temizler, ardından tüm dinleyen TCP uç noktalarını yeniden tarar.

### Settings

Otomatik yenileme, yenileme aralığı, duplicate binding birleştirme, sistem süreçlerini gösterme ve süreç sonlandırma onayı gibi ayarları uygular ve kaydeder.

## Çekirdek test

```bash
python core_test.py
```

Test geçici bir localhost TCP listener açar, tarama yapar ve bu listener'ın Python process'i ile eşleştirilebildiğini doğrular.

Başarılı sonuç şu ifadeyle başlar:

```text
PASS
```

## Proje yapısı

```text
.
├── RUN_THIS_Localhost_Radar_v0.3.pyw  # sessiz Windows başlatıcı
├── main.py                             # uygulama giriş noktası
├── core_test.py                        # localhost algılama smoke testi
├── requirements.txt
├── src/
│   ├── main_window.py                  # PySide6 arayüzü ve tarama akışı
│   ├── models.py                       # port/process modelleri ve sınıflandırma
│   ├── port_scanner.py                 # dinleyen TCP portlarını bulma
│   ├── process_manager.py              # süreç bilgisi ve güvenli sonlandırma
│   └── settings_manager.py             # kalıcı ayarlar
└── *.bat                               # kurulum, debug ve test yardımcıları
```

## Gizlilik ve çalışma biçimi

Localhost Radar yerel bir masaüstü aracıdır. Bulut backend'i, arka plan servisi veya tray agent gerektirmez. Tarama işlemi `psutil` aracılığıyla yerel TCP listener bilgilerini ve yerel süreç metadatasını okur.

Windows'ta bazı süreç bilgileri için yönetici yetkisi gerekebilir. Listener veya süreç bilgisine erişim reddedilirse uygulamayı Yönetici olarak çalıştırmak gerekebilir.

## Sürüm

Güncel sürüm: **v0.3.0 — BUILD 2026-08-30-B**

Değişiklikler için [CHANGELOG.md](CHANGELOG.md) dosyasına bakabilirsin.

## Lisans

Henüz bir lisans seçilmedi. Lisans eklenene kadar kaynak kod, depo sahibinin varsayılan telif hakları kapsamında kalır.
