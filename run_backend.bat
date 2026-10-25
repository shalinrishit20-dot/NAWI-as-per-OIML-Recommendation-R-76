@echo off

if not defined SECRET_KEY (
  echo ERROR: SECRET_KEY must be set in the current shell before starting NAWI.
  exit /b 1
)

set NAWI_SESSION_COOKIE_SECURE=0
cd /d "%~dp0backend"
if not exist venv python -m venv venv
call venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
pause
