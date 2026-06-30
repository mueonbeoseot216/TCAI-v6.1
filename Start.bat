@echo off
setlocal

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

echo.
echo   [TCAI v6] %ROOT%

rem --- Find Python ---
set "PYTHON=%ROOT%\tools\python-venv\python.exe"
if exist "%PYTHON%" goto :run

echo   [ERROR] Python not found at: %PYTHON%
pause
exit /b 1

:run
echo   [TCAI v6] Python: %PYTHON%

rem --- Load .env ---
if exist "%ROOT%\home\.env" (
    for /f "usebackq tokens=1,2 delims==" %%a in ("%ROOT%\home\.env") do (
        set "%%a=%%b"
    )
)

if not defined TCAI_MODEL set "TCAI_MODEL=deepseek-v4-pro"
echo   [TCAI v6] Model: %TCAI_MODEL%
echo.

rem --- Runtime dirs ---
if not exist "%ROOT%\records" mkdir "%ROOT%\records"
if not exist "%ROOT%\work"    mkdir "%ROOT%\work"

rem --- Launch ---
set "THINCORE_ROOT=%ROOT%"
set "HOME=%ROOT%\home"
set "PYTHONDONTWRITEBYTECODE=1"

"%PYTHON%" -u "%ROOT%\launcher.py"

echo.
echo   [TCAI v6] Exited.
pause
