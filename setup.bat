@echo off
setlocal

echo Creating virtual environment...
:: Create a virtual environment named 'venv'
python -m venv venv

echo Activating virtual environment...
:: Activate the virtual environment
call venv\Scripts\activate.bat

echo Upgrading pip...
:: Ensure pip is up to date
python -m pip install --upgrade pip

echo Installing requirements...
:: Install dependencies from requirements.txt
if exist requirements.txt (
    pip install -r requirements.txt
    echo Setup complete! The virtual environment is ready.
) else (
    echo Error: requirements.txt not found in the current directory.
    exit /b 1
)

echo.
echo To activate this environment in the future, run:
echo venv\Scripts\activate.bat

endlocal