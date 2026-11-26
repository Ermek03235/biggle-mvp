@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python
py -3 beagle.py
goto done
:python
python beagle.py
:done
if errorlevel 1 pause
