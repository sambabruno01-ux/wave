@echo off
title Установка библиотек Wave
echo ==============================================
echo       Шаг 2: Установка зависимостей Wave
echo ==============================================

echo [*] Обновление pip...
python -m pip install --upgrade pip

echo.
echo [*] Установка зависимостей...
python -m pip install PyQt6 "PyQt6-Fluent-Widgets[full]" requests sounddevice numpy websockets

echo.
echo ==============================================
echo [+] Все библиотеки успешно установлены!
echo [+] Запускайте 'Wave.bat' в корневой папке.
echo ==============================================
pause
