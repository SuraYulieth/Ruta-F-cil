# Script para gestionar el proyecto Ruta Fácil
# Uso: .\manage.ps1 [start|stop|restart|init]

param (
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("start", "stop", "restart", "init", "status")]
    $Action
)

$BackendPort = 8000
$FrontendPort = 5173

function Get-ProcessByPort($Port) {
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($connection) {
            return Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
        }
    } catch {}
    return $null
}

function Stop-Project {
    Write-Host "`n[!] Deteniendo el proyecto..." -ForegroundColor Yellow
    
    # Detener Backend
    $backend = Get-ProcessByPort $BackendPort
    if ($backend) {
        Write-Host "[-] Deteniendo Backend (PID: $($backend.Id))..." -ForegroundColor Gray
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Backend detenido." -ForegroundColor Green
    } else {
        Write-Host "[?] El Backend no parece estar en ejecución en el puerto $BackendPort." -ForegroundColor Gray
    }

    # Detener Frontend (Vite)
    $frontend = Get-ProcessByPort $FrontendPort
    if ($frontend) {
        Write-Host "[-] Deteniendo Frontend (PID: $($frontend.Id))..." -ForegroundColor Gray
        Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Frontend detenido." -ForegroundColor Green
    } else {
        Write-Host "[?] El Frontend no parece estar en ejecución en el puerto $FrontendPort." -ForegroundColor Gray
    }
}

function Start-Project {
    Write-Host "`n[*] Iniciando el proyecto Ruta Fácil..." -ForegroundColor Cyan
    
    # Verificar si ya están corriendo
    if (Get-ProcessByPort $BackendPort) {
        Write-Host "[!] El puerto $BackendPort ya está ocupado. ¿Ya está el backend corriendo?" -ForegroundColor Yellow
    } else {
        Write-Host "[+] Lanzando Backend (Django)..." -ForegroundColor Magenta
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; python manage.py runserver $BackendPort" -WindowStyle Normal
    }

    if (Get-ProcessByPort $FrontendPort) {
        Write-Host "[!] El puerto $FrontendPort ya está ocupado. ¿Ya está el frontend corriendo?" -ForegroundColor Yellow
    } else {
        Write-Host "[+] Lanzando Frontend (Vite)..." -ForegroundColor Magenta
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -WindowStyle Normal
    }

    Write-Host "`n[OK] Servicios lanzados." -ForegroundColor Green
    Write-Host "--------------------------------------"
    Write-Host "Frontend: http://localhost:$FrontendPort"
    Write-Host "Backend:  http://localhost:$BackendPort/admin"
    Write-Host "--------------------------------------"
}

function Init-Project {
    Write-Host "`n[*] Inicializando entorno del proyecto..." -ForegroundColor Cyan
    
    # 1. Backend Setup
    Write-Host "`n[1/4] Configurando Backend..." -ForegroundColor Magenta
    if (-not (Test-Path "backend\venv")) {
        Write-Host "Creando entorno virtual (venv)..."
        python -m venv backend\venv
    }
    
    Write-Host "Instalando dependencias base del Backend..."
    & backend\venv\Scripts\python.exe -m pip install django djangorestframework django-cors-headers
    
    Write-Host "Aplicando migraciones a la base de datos..."
    & backend\venv\Scripts\python.exe backend\manage.py migrate
    
    if (Test-Path "backend\seed.py") {
        Write-Host "Poblando base de datos con datos iniciales..."
        & backend\venv\Scripts\python.exe backend\seed.py
    }

    # 2. Frontend Setup
    Write-Host "`n[2/4] Configurando Frontend..." -ForegroundColor Magenta
    if (-not (Test-Path "frontend\node_modules")) {
        Write-Host "Instalando paquetes de npm (esto puede tardar)..."
        cd frontend
        npm install
        cd ..
    } else {
        Write-Host "Node modules ya existen. Saltando npm install."
    }

    Write-Host "`n[OK] Inicialización completada correctamente." -ForegroundColor Green
    Write-Host "Ahora puedes usar: .\manage.ps1 start" -ForegroundColor Gray
}

function Get-Status {
    Write-Host "`n[*] Estado del Proyecto:" -ForegroundColor Cyan
    $b = Get-ProcessByPort $BackendPort
    $f = Get-ProcessByPort $FrontendPort

    if ($b) { Write-Host "[RUNNING] Backend (PID: $($b.Id)) en puerto $BackendPort" -ForegroundColor Green }
    else { Write-Host "[STOPPED] Backend en puerto $BackendPort" -ForegroundColor Red }

    if ($f) { Write-Host "[RUNNING] Frontend (PID: $($f.Id)) en puerto $FrontendPort" -ForegroundColor Green }
    else { Write-Host "[STOPPED] Frontend en puerto $FrontendPort" -ForegroundColor Red }
}

# Lógica principal
switch ($Action) {
    "start"   { Start-Project }
    "stop"    { Stop-Project }
    "restart" { Stop-Project; Start-Sleep -Seconds 1; Start-Project }
    "init"    { Init-Project }
    "status"  { Get-Status }
}
