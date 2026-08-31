@echo off
cd /d "%~dp0"
py -m k88fr.gui
if errorlevel 1 pause
