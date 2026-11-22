@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py gui.py
) else (
    python gui.py
)
if errorlevel 1 (
    echo.
    echo No se pudo iniciar la aplicacion. Verifique Python 3 y tkinter.
    pause
)
