@echo off
setlocal
cd /d "%~dp0"

set "SONAR_PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%SONAR_PYTHON%" (
    echo Python environment not found:
    echo %SONAR_PYTHON%
    echo.
    echo Create .venv and install requirements.txt first.
    pause
    exit /b 1
)

if /I "%~1"=="--check" (
    "%SONAR_PYTHON%" -B "%~dp0main.py" --help >nul
    if errorlevel 1 (
        echo Launcher check failed.
        exit /b 1
    )
    echo Launcher check passed.
    exit /b 0
)

"%SONAR_PYTHON%" -B "%~dp0main.py" gui
set "SONAR_EXIT_CODE=%ERRORLEVEL%"

if not "%SONAR_EXIT_CODE%"=="0" (
    echo.
    echo Program exited with error code: %SONAR_EXIT_CODE%
    pause
)

exit /b %SONAR_EXIT_CODE%
