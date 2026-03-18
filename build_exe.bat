@echo off
echo.
echo ========================================
echo Compilando para EXE com PyInstaller
echo ========================================
echo.

REM Verificar se PyInstaller está instalado
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller não encontrado. Instalando...
    pip install pyinstaller
)

echo.
echo Gerando executável...
echo.

REM Criar executável
pyinstaller --onefile ^
    --windowed ^
    --name "Google Drive Downloader" ^
    --icon=icon.ico ^
    --add-data ".:." ^
    downloader_gui.pyw

echo.
echo ========================================
echo Compilação concluída!
echo O executável está em: dist\Google Drive Downloader.exe
echo ========================================
echo.

pause
