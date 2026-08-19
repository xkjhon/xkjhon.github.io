@echo off
title eCobOne — Dashboard Auto-Updater ^& Git Publisher (10 min)
color 0A

echo ============================================================
echo   eCobOne — Sistema de Atualização Automática ^& Git Push
echo   Frequência: Executar ^& publicar no Git a cada 10 minutos
echo ============================================================
echo.

:loop
echo ------------------------------------------------------------
echo [%date% %time%] Iniciando ciclo de atualização do eCobOne...
echo ------------------------------------------------------------

:: 1. Ir para a pasta do Updater e rodar o Python
cd /d "%~dp0eCobOne\Python-Updater"
python updater.py

:: 2. Voltar para a raiz do repositório
cd /d "%~dp0"

:: 3. Publicar dados e alterações atualizadas no GitHub
echo.
echo [%date% %time%] Publicando dados atualizados no GitHub...
git add .
git commit -m "Auto-update dados.txt - %date% %time%"
git push origin main

echo.
echo [%date% %time%] Ciclo concluido com sucesso!
echo Aguardando 10 minutos (600s) ate o proximo ciclo...
echo Pressione Ctrl+C se desejar encerrar a atualizacao automatica.
echo ------------------------------------------------------------
echo.

:: 4. Aguardar 600 segundos (10 minutos) sem interromper
timeout /t 600 /nobreak

goto loop
