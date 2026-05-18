@echo off
setlocal

echo Checking for Python 3.12...
:: Attempt to check the version of Python 3.12
py -3.12 --version >nul 2>&1

if %errorlevel% neq 0 (
    echo =======================================================
    echo ERROR: Python 3.12 is required but could not be found.
    echo Your current default Python version is likely 3.14.
    echo.
    echo Please download and install Python 3.12 from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, make sure to check the 
    echo box that says "Add python.exe to PATH".
    echo =======================================================
    pause
    exit /b 1
)

echo Creating virtual environment using Python 3.12...
py -3.12 -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing requirements...
if exist requirements.txt (
    pip install -r requirements.txt
    echo.
    echo Setup complete! The virtual environment is ready and running Python 3.12.
) else (
    echo Error: requirements.txt not found in the current directory.
    exit /b 1
)

echo.
echo To activate this environment in the future, run:
echo venv\Scripts\activate.bat

endlocal