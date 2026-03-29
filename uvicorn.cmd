@echo off
setlocal
cd /d "%~dp0aira"
"%~dp0.venv\Scripts\python.exe" -m uvicorn %*
