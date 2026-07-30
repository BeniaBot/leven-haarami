@echo off
rem בניית EXE של לבן הארמי V6.4 Ultra
rem דורש: pip install pyinstaller pywebview pillow
cd /d "%~dp0"
pyinstaller --onefile --windowed --name "Leven Haarami V6.4 Ultra" --icon icon.ico --add-data "index.html;." --add-data "icon.ico;." desktop.py --noconfirm
echo.
echo הסתיים. הקובץ נמצא ב: dist\Leven Haarami V6.4 Ultra.exe
pause
