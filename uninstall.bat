@echo off
setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
set "DATA_DIR=%TEMP%\jarvis_ultron_assistant"

echo ============================================
echo   Jarvis V2 - Desinstalador
echo ============================================
echo.
echo Isso remove o ambiente virtual (.venv) criado pelo install.bat.
echo O codigo-fonte do projeto NAO sera apagado.
echo.

set /p CONFIRM="Deseja continuar? (S/N): "
if /I not "%CONFIRM%"=="S" (
    echo Operacao cancelada.
    goto :end
)

if exist ".venv" (
    echo Removendo ambiente virtual .venv ...
    rmdir /s /q ".venv"
    echo Ambiente virtual removido.
) else (
    echo Nenhum ambiente virtual .venv encontrado.
)

echo.
echo O Jarvis V2 tambem guarda memoria, perfil e crencas aprendidas em:
echo   %DATA_DIR%
echo.
set /p REMOVE_DATA="Deseja apagar tambem esses dados aprendidos? (S/N): "
if /I "%REMOVE_DATA%"=="S" (
    set /p CONFIRM2="Essa acao nao pode ser desfeita. Confirma? (S/N): "
    if /I "!CONFIRM2!"=="S" (
        if exist "%DATA_DIR%" (
            rmdir /s /q "%DATA_DIR%"
            echo Dados aprendidos removidos.
        ) else (
            echo Nenhum dado encontrado em %DATA_DIR%.
        )
    ) else (
        echo Remocao de dados cancelada. Apenas o ambiente virtual foi removido.
    )
) else (
    echo Dados aprendidos preservados em %DATA_DIR%.
)

echo.
echo ============================================
echo   Desinstalacao concluida.
echo   Para reinstalar, rode install.bat novamente.
echo ============================================

:end
