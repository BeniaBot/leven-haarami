@echo off
rem בניית EXE של לבן הארמי 3.0
rem דורש: pip install pyinstaller pywebview pillow
cd /d "%~dp0"
pyinstaller --onefile --windowed --name "Leven Haarami 3.0" --icon icon.ico --add-data "index.html;." --add-data "icon.ico;." desktop.py --noconfirm
echo.
echo הסתיים. הקובץ נמצא ב: dist\Leven Haarami 3.0.exe
pause
