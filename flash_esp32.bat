@echo off
REM ESP32 Flash Script for Windows
REM Usage: flash_esp32.bat [receiver|transmitter] [port]

if "%2"=="" (
    echo Usage: %0 [receiver^|transmitter] [port]
    echo Example: %0 receiver COM3
    echo Example: %0 transmitter COM4
    exit /b 1
)

set DEVICE_TYPE=%1
set PORT=%2

if "%DEVICE_TYPE%"=="receiver" (
    set BUILD_DIR=.pio\build\esp32dev-receiver
    echo Flashing ESP32-32E Display Board (receiver) to %PORT%...
) else if "%DEVICE_TYPE%"=="transmitter" (
    set BUILD_DIR=.pio\build\esp32dev-transmitter
    echo Flashing ESP32 transmitter to %PORT%...
) else (
    echo Invalid device type. Use 'receiver' or 'transmitter'
    exit /b 1
)

REM Check if binaries exist
if not exist "%BUILD_DIR%\firmware.bin" (
    echo Error: Firmware binaries not found in %BUILD_DIR%
    echo Please run 'pio run -e esp32dev-%DEVICE_TYPE%' first
    exit /b 1
)

echo Using binaries from: %BUILD_DIR%
echo Port: %PORT%
echo.

REM Flash the ESP32
esptool.py --chip esp32 --port %PORT% --baud 921600 write_flash ^
    0x1000 "%BUILD_DIR%\bootloader.bin" ^
    0x8000 "%BUILD_DIR%\partitions.bin" ^
    0x10000 "%BUILD_DIR%\firmware.bin"

if %errorlevel% equ 0 (
    echo.
    echo ✅ Flash successful!
    echo You can now monitor the device with:
    echo    pio device monitor -p %PORT% -b 115200
) else (
    echo.
    echo ❌ Flash failed! Check your connection and port.
    echo Troubleshooting:
    echo - Make sure ESP32 is connected
    echo - Try holding BOOT button while pressing RESET
    echo - Verify the correct port
)