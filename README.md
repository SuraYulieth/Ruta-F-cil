# Ruta Facil

Sistema de logistica con optimizacion de rutas y modulo operativo para repartidores.

## Stack

- Backend: Django + DRF + TokenAuthentication
- Frontend: React + Vite
- Base de datos local: SQLite (desarrollo)

## Estructura principal

- backend
- frontend
- docs
- documentacion

## Requisitos

- Python 3.12+
- Node.js 20+
- npm 10+

## Inicio rapido

### 1) Backend

Desde la carpeta backend:

```powershell
c:/Users/suray/OneDrive/Escritorio/Ruta-F-cil/.venv/Scripts/python.exe manage.py migrate
c:/Users/suray/OneDrive/Escritorio/Ruta-F-cil/.venv/Scripts/python.exe manage.py runserver 8000
```

### 2) Frontend

Desde la carpeta frontend:

```powershell
npm install
npm run dev
```

## Modulo repartidores (implementado)

Endpoints principales:

- POST /api/login/
- GET /api/drivers/me/
- POST /api/drivers/me/toggle-availability/
- GET /api/drivers/me/orders/
- GET /api/drivers/me/routes/
- POST /api/drivers/me/location/
- POST /api/drivers/me/orders/{id}/start/
- POST /api/drivers/me/orders/{id}/deliver/

## Pruebas

Desde la carpeta backend:

```powershell
c:/Users/suray/OneDrive/Escritorio/Ruta-F-cil/.venv/Scripts/python.exe manage.py test logistics.tests --verbosity 1
```

Estado validado en esta entrega:

- Suite modulo logistics: 24/24 OK
- Driver API tests: 11/11 OK

## Documentacion relacionada

- AUDITORIA_MODULO_REPARTIDORES.md
- FASE2_BACKEND_INFRASTRUCTURE.md
- RESUMEN_EJECUTIVO_PROGRESO.md
- backend/ENTREGA_COMPLETA.md