@echo off
setlocal
rem Refresh PATH from the registry so newly installed tools (FFmpeg, Deno) are found
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%P"
cd /d "%~dp0"
".\env\Scripts\python.exe" -m streamlit run app.py
pause
