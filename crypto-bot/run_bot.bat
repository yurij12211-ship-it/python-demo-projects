@echo off
cd /d %~dp0
if not exist .env copy .env.example .env >nul & echo Vpyshit BOT_TOKEN u fail .env i zapustit znovu & notepad .env & exit /b
python -m pip install -q -r requirements.txt
python bot.py
pause
