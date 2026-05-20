@echo off
echo =========================================
echo    Cleaning up __pycache__ folders...
echo =========================================

:: Recursively search for and delete __pycache__ directories
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        echo Deleting: %%d
        rd /s /q "%%d"
    )
)

echo.
echo Cleanup complete!
pause