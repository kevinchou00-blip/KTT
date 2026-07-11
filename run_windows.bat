@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m research.main
if errorlevel 1 pause
