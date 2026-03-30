@echo off
echo ============================================================
echo   DocPopular - Build Completo (PyInstaller + Instalador)
echo ============================================================

REM Ativa o venv
if not exist venv (
    echo [0/3] Criando venv e instalando dependencias...
    python -m venv venv
    venv\Scripts\python.exe -m pip install -r requirements.txt
)
call venv\Scripts\activate.bat

REM Tenta fechar o app e o compilador se estiverem abertos
taskkill /F /IM DocPopular.exe /T >nul 2>&1
taskkill /F /IM ISCC.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

REM Limpa pastas de build anteriores para evitar erros de permissao
if exist build (
    echo [+] Limpando pasta build anterior...
    rmdir /s /q build >nul 2>&1
)
if exist dist (
    echo [+] Limpando pasta dist anterior...
    rmdir /s /q dist >nul 2>&1
)

REM Limpa a pasta installer para novos artefatos
if exist installer (
    echo [+] Limpando pasta installer...
    del /q installer\* >nul 2>&1
) else (
    mkdir installer
)

REM Extrai a versao do version.py usando python
for /f %%I in ('python -c "from version import APP_VERSION; print(APP_VERSION)"') do set APP_VERSION=%%I
echo [+] Versao detectada: v%APP_VERSION%
echo.

echo [1/4] Compilando o aplicativo com PyInstaller...
python -m PyInstaller --clean --noconfirm DocPopular.spec
if errorlevel 1 (
    echo ERRO: falha ao gerar o aplicativo.
    pause & exit /b 1
)
echo     OK - dist\DocPopular\

echo.
echo [2/4] Gerando instalador com Inno Setup...
python _gerar_iss.py

REM Procura o compilador do Inno Setup
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
    echo AVISO: Inno Setup nao encontrado.
    echo Instale em: https://jrsoftware.org/isdl.php
    echo Depois execute novamente ou compile manualmente: DocPopular.iss
    pause & exit /b 0
)

"%ISCC%" DocPopular.iss
if errorlevel 1 (
    echo ERRO: falha ao gerar o instalador.
    pause & exit /b 1
)

echo.
echo [3/4] Criando pacote ZIP para auto-update...
timeout /t 2 /nobreak >nul
set ZIP_BASE_NAME=DocPopular
if exist "installer\%ZIP_BASE_NAME%.zip" del "installer\%ZIP_BASE_NAME%.zip"
python -c "import shutil; shutil.make_archive('installer/%ZIP_BASE_NAME%', 'zip', 'dist/DocPopular')"
if errorlevel 1 (
    echo ERRO: falha ao gerar o arquivo ZIP.
    pause & exit /b 1
)
echo     OK - installer\%ZIP_BASE_NAME%.zip (v%APP_VERSION%)

echo.
echo [4/5] Finalizando Metadados de Segurança...
python scripts\finalize_release.py
if errorlevel 1 (
    echo ERRO: falha ao gerar assinaturas SHA256.
    pause & exit /b 1
)

echo.
echo [5/5] Limpeza pos-build...
echo [+] Removendo pastas temporarias (build/dist)...
rmdir /s /q build >nul 2>&1
rmdir /s /q dist >nul 2>&1
echo     Concluido.

echo.
echo ============================================================
echo   BUILD COMPLETO E ASSINADO!
echo ============================================================
echo.
echo  Instalador:  installer\DocPopular_Setup_v%APP_VERSION%.exe
echo  Auto-update: installer\DocPopular.zip
echo  Metadata:    version.json (Hashes Atualizados!)
echo.
echo  IMPORTANTE: 
echo  1. Envie o .exe para novos clientes.
echo  2. Carregue o .zip E o arquivo version.json no GitHub Releases 
echo     como 'DocPopular.zip' para assegurar atualizacoes autenticadas.
echo ============================================================
pause
