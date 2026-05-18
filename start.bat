@echo off
echo =========================================
echo    Starting AI Tri-Coach Server...
echo =========================================

:: Activate the virtual environment
call venv\Scripts\activate.bat

:: Start the FastAPI server
uvicorn backend.main:app --reload

pause