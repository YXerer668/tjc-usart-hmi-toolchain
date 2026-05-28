@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_touchsafe_pipeline.ps1" %*
exit /b %errorlevel%
