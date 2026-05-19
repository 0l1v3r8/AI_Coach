@echo off
setlocal

echo Checking for Python 3.12...
:: Attempt to check the version of Python 3.12
py -3.12 --version >nul 2>&1

if %errorlevel% neq 0 (
    echo =======================================================
    echo Python 3.12 was not found. 
    echo Downloading and installing Python 3.12 automatically...
    echo =======================================================
    
    :: Download Python 3.12 installer using built-in curl
    curl -o python-3.12-installer.exe https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe
    
    if not exist python-3.12-installer.exe (
        echo ERROR: Failed to download the Python installer. Check your internet connection.
        pause
        exit /b 1
    )
    
    echo Installing Python 3.12... Please wait, this may take a few minutes.
    :: Run installer silently, add to PATH, and install for current user to avoid UAC admin prompts
    start /wait python-3.12-installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    
    echo Installation finished. Cleaning up installer file...
    del python-3.12-installer.exe
    
    :: Verify the installation was successful
    py -3.12 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo =======================================================
        echo ERROR: Python 3.12 installation failed, or the 'py' launcher hasn't registered it yet.
        echo You may need to restart this command prompt or install it manually.
        echo =======================================================
        pause
        exit /b 1
    )
    echo Python 3.12 installed successfully!
    echo.
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