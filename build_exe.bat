@echo off
setlocal

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

"%PYTHON%" -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    "%PYTHON%" -m pip install pyinstaller
)

"%PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --onefile ^
    --name "Project for AI" ^
    --hidden-import matplotlib.backends.backend_qtagg ^
    --hidden-import PyQt6.sip ^
    main.py

echo.
echo Build finished: dist\Project for AI.exe
endlocal
