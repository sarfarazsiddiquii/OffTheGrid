@echo off
REM Build svchost_helper.exe (no console window, single file)
REM Usage: double-click build.bat from inside the OffTheGrid folder

pip install -r requirements.txt
pyinstaller --onefile --noconsole --name svchost_helper svchost_helper.py
echo.
echo Done!  Find the binary at:  dist\svchost_helper.exe
pause
