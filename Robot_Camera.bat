@echo off
:: Lệnh này tự động lấy đường dẫn của chính thư mục chứa file .bat này
cd /d "%~dp0"

echo Dang khoi dong Robot Camera...
echo --------------------------------

:: Chạy trực tiếp Python từ môi trường ảo mà không cần lệnh "activate"
".venv\Scripts\python.exe" main.py

echo.
pause