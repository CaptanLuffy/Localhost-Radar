@echo off
cd /d "%~dp0"
echo [Localhost Radar v0.3] Gerekli Python paketleri kuruluyor...
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Kurulum basarisiz.
  pause
  exit /b 1
)
echo.
echo Kurulum tamamlandi. Bundan sonra RUN_THIS_Localhost_Radar_v0.3.pyw dosyasina cift tikla.
pause
