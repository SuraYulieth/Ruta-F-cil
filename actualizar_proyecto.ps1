param(
    [string]$Branch = "main",
    [switch]$SkipDependencies = $false,
    [switch]$SkipMigrations = $false
)

$ErrorActionPreference = "Stop"
$projectRoot = Get-Location

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "   ACTUALIZAR PROYECTO DESDE GIT" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Validar que estamos en un repositorio Git
if (-not (Test-Path ".git")) {
    Write-Host "❌ ERROR: No se encontró repositorio Git en la carpeta actual." -ForegroundColor Red
    Write-Host "   Ejecuta este script desde la raíz del proyecto." -ForegroundColor Red
    exit 1
}

Write-Host "📁 Carpeta actual: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# 1. Actualizar código desde Git
Write-Host "1️⃣  Obteniendo cambios desde Git..." -ForegroundColor Cyan
try {
    git fetch origin
    git pull origin $Branch --rebase
    Write-Host "✅ Git actualizado correctamente" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR al actualizar desde Git: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. Actualizar dependencias del Backend (Python)
if (-not $SkipDependencies) {
    if (Test-Path "backend/requirements.txt") {
        Write-Host "2️⃣  Actualizando dependencias del Backend..." -ForegroundColor Cyan
        try {
            Push-Location backend
            
            # Verificar si hay un entorno virtual
            $venvPath = if (Test-Path "venv") { "venv" } elseif (Test-Path ".venv") { ".venv" } else { $null }
            
            if ($venvPath) {
                Write-Host "   📦 Entorno virtual encontrado: $venvPath" -ForegroundColor Yellow
                & "$venvPath\Scripts\pip" install -r requirements.txt
            } else {
                Write-Host "   ⚠️  No se encontró entorno virtual. Usa python -m pip directamente." -ForegroundColor Yellow
                python -m pip install -r requirements.txt
            }
            
            Pop-Location
            Write-Host "✅ Dependencias del Backend actualizadas" -ForegroundColor Green
        } catch {
            Write-Host "❌ ERROR al actualizar dependencias del Backend: $_" -ForegroundColor Red
            Pop-Location
            exit 1
        }
    } else {
        Write-Host "⚠️  No se encontró requirements.txt en backend/" -ForegroundColor Yellow
    }
} else {
    Write-Host "2️⃣  (Omitiendo actualización de dependencias del Backend - Flag: SkipDependencies)" -ForegroundColor Gray
}

Write-Host ""

# 3. Actualizar dependencias del Frontend (Node.js)
if (-not $SkipDependencies) {
    if (Test-Path "frontend/package.json") {
        Write-Host "3️⃣  Actualizando dependencias del Frontend..." -ForegroundColor Cyan
        try {
            Push-Location frontend
            npm install
            Pop-Location
            Write-Host "✅ Dependencias del Frontend actualizadas" -ForegroundColor Green
        } catch {
            Write-Host "❌ ERROR al actualizar dependencias del Frontend: $_" -ForegroundColor Red
            Pop-Location
            exit 1
        }
    } else {
        Write-Host "⚠️  No se encontró package.json en frontend/" -ForegroundColor Yellow
    }
} else {
    Write-Host "3️⃣  (Omitiendo actualización de dependencias del Frontend - Flag: SkipDependencies)" -ForegroundColor Gray
}

Write-Host ""

# 4. Ejecutar migraciones del Backend (Django)
if (-not $SkipMigrations) {
    if (Test-Path "backend/manage.py") {
        Write-Host "4️⃣  Ejecutando migraciones de Base de Datos..." -ForegroundColor Cyan
        try {
            Push-Location backend
            
            $venvPath = if (Test-Path "venv") { "venv" } elseif (Test-Path ".venv") { ".venv" } else { $null }
            
            if ($venvPath) {
                & "$venvPath\Scripts\python" manage.py migrate
            } else {
                python manage.py migrate
            }
            
            Pop-Location
            Write-Host "✅ Migraciones ejecutadas correctamente" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  ADVERTENCIA al ejecutar migraciones: $_" -ForegroundColor Yellow
            Pop-Location
        }
    } else {
        Write-Host "⚠️  No se encontró manage.py en backend/" -ForegroundColor Yellow
    }
} else {
    Write-Host "4️⃣  (Omitiendo migraciones de Base de Datos - Flag: SkipMigrations)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "   ✅ ACTUALIZACIÓN COMPLETADA" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Rama actualizada: $Branch" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "  • Backend:   cd backend && python manage.py runserver" -ForegroundColor White
Write-Host "  • Frontend:  cd frontend && npm run dev" -ForegroundColor White
Write-Host ""
