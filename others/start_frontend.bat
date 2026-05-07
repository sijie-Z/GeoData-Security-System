@echo off
chcp 65001 >nul
cd /d "%~dp0testrealfrontol"
npm run dev
pause
