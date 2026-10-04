@echo off
cd /d %~dp0
echo ==========================================
echo   LM system - add indexes for daily_data
echo ==========================================
echo.
if not exist venv (
  echo [ERROR] venv not found. Please run run.bat once first.
  pause
  exit /b 1
)
echo [WARN] Please stop the system first (press Ctrl+C in the run.bat window).
echo.
call venv\Scripts\activate.bat
python -m app.add_indexes
echo.
echo Done. You can now restart the system with run.bat.
pause
