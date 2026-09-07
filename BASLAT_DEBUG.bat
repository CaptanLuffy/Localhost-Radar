@echo off
cd /d "%~dp0"
echo Localhost Radar v0.3 DEBUG - BUILD 2026-08-30-B
py main.py
if errorlevel 1 pause
