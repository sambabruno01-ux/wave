@echo off
title Установка Python
echo ==============================================
echo       Шаг 1: Проверка и установка Python
echo ==============================================

python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [+] Python уже установлен в системе!
    echo.
    pause
    exit /b
)

echo [!] Python не найден. Скачивание официального установщика...
curl -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

echo [!] Установка Python (добавление в PATH)...
start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

del python_installer.exe
echo.
echo [+] Python успешно установлен!
echo [!] Закройте это окно и запустите '2_install_libraries.bat'.
echo.
pause
