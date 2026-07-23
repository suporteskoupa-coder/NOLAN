@echo off
setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo ============================================
echo   Nolan - Instalador de dependencias
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo Instale o Python 3.11+ em https://www.python.org/downloads/ e tente novamente.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual em .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        exit /b 1
    )
) else (
    echo Ambiente virtual .venv ja existe. Reutilizando.
)

echo.
echo Atualizando pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo.
echo Instalando dependencias do requirements.txt...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar uma ou mais dependencias.
    echo Verifique sua conexao com a internet e tente novamente.
    exit /b 1
)

echo.
echo ============================================
echo   Instalacao concluida com sucesso.
echo.
echo   Proximos passos:
echo   1. Instale o Ollama: https://ollama.com/download
echo   2. Baixe um modelo local, por exemplo:
echo        ollama pull llama3
echo   3. Use start_assistant.bat para iniciar o Nolan.
echo ============================================
