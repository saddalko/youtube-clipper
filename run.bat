@echo off
setlocal
rem Refresh PATH from the registry so newly installed tools (FFmpeg, Deno) are found
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%P"
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app.py
) else if exist "env\Scripts\python.exe" (
    "env\Scripts\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)
pause
