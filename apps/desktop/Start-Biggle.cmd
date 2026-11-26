@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python
py -3 biggle.py
goto done
:python
python biggle.py
:done
if errorlevel 1 pause
