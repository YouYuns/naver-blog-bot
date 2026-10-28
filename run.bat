@echo off
cd /d "%~dp0"
"C:\Users\SUNGHO\AppData\Local\Programs\Python\Python312\python.exe" app.py
if %ERRORLEVEL% NEQ 0 pause
