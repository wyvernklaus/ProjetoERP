@echo off
:: Navega até a pasta raiz do projeto
cd /d "D:\business _network"

:: JANELA 1: Ativa o ambiente virtual e liga o servidor
echo Iniciando o servidor...
start "Servidor Business" cmd /k "call .\venv\Scripts\activate.bat && python main.py"

:: ligar servidor
start tailscale funnel 8000
echo Tudo pronto! As janelas do Axon e do zgrok foram iniciadas.
pause