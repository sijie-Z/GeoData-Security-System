@echo off
chcp 65001 >nul
cd /d "%~dp0testrealend"
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
)
python app.py
if errorlevel 1 (
  py -3 app.py
)
pause
