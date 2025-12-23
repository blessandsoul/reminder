@echo off
cd /d "%~dp0"
echo Killing old bot instances...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
echo Starting Reminder Bot...
python bot.py
pause
