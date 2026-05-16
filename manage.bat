@echo off
:: Script de conveniencia para ejecutar manage.ps1
:: Uso: manage start | manage stop | manage init | manage status

set ACTION=%1
if "%ACTION%"=="" (
    echo Uso: manage [start^|stop^|restart^|init^|status]
    set ACTION=status
)

powershell -ExecutionPolicy Bypass -File ".\manage.ps1" %ACTION%
