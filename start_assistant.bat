@echo off
setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set "PYTHON_EXE="
set "OLLAMA_EXE=ollama"
set "WINDOWS_PYTHON=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
set "WINDOWS_OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else if exist "%WINDOWS_PYTHON%" (
    set "PYTHON_EXE=%WINDOWS_PYTHON%"
) else (
    echo [ERRO] Python nao encontrado.
    echo Instale o Python ou crie uma .venv para este projeto.
    exit /b 1
)

if exist "%WINDOWS_OLLAMA%" (
    set "OLLAMA_EXE=%WINDOWS_OLLAMA%"
)

"%PYTHON_EXE%" -c "import customtkinter, pyautogui, sounddevice, scipy" >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Dependencias Python nao disponiveis para o interpretador selecionado.
    echo Rode install.bat para instalar tudo automaticamente.
    exit /b 1
)

"%OLLAMA_EXE%" list >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Ollama nao encontrado ou nao respondeu corretamente.
    echo Verifique se o Ollama esta instalado e com pelo menos um modelo local.
    exit /b 1
)

"%PYTHON_EXE%" main.py
