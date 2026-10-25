@echo off
cd /d "%~dp0"

if not defined SECRET_KEY (
  echo ERROR: SECRET_KEY must be set in the current shell before starting NAWI.
  exit /b 1
)

start "NAWI Backend" cmd /k call run_backend.bat
timeout /t 2 /nobreak >nul
start "NAWI Frontend" cmd /k call run_frontend.bat
