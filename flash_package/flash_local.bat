@echo off
REM Flash ESP32 from local machine (Windows)
REM Usage: flash_local.bat [PORT]
REM Example: flash_local.bat COM3

set PORT=%1
if "%PORT%"=="" set PORT=COM3

echo Flashing ESP32 on port: %PORT%
echo.

REM Check if Python is available
python --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check if esptool is installed, if not install it
python -m esptool version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing esptool...
    pip install esptool
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to install esptool
        pause
        exit /b 1
    )
)

echo.
echo Starting flash process...
echo Hold the BOOT button on your ESP32 if flash fails
echo.

REM Flash the binaries
python -m esptool --chip esp32 --port %PORT% --baud 460800 ^
    --before default_reset --after hard_reset write_flash -z ^
    --flash_mode dio --flash_freq 40m --flash_size detect ^
    0x1000 bootloader.bin ^
    0x8000 partition-table.bin ^
    0x10000 3.2inch_ESP32_LVGL.bin

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Flash completed successfully!
    echo ========================================
    echo Your ESP32 should now be running the LVGL demo.
    echo If the screen is blank, press the RESET button.
) else (
    echo.
    echo ========================================
    echo Flash FAILED!
    echo ========================================
    echo Troubleshooting tips:
    echo 1. Hold the BOOT button while flashing
    echo 2. Check the COM port in Device Manager
    echo 3. Try a different USB cable
    echo 4. Use a lower baud rate: change 460800 to 115200
)

echo.
pause
