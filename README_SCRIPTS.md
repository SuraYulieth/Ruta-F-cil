# Scripts de Gestión del Proyecto

He creado scripts de PowerShell para facilitarte la vida al trabajar con el proyecto. Estos scripts te permiten inicializar el entorno, arrancar los servicios y detenerlos con comandos simples.

## Requisitos
- **PowerShell**: Viene por defecto en Windows.
- **Python**: Instalado y en el PATH.
- **Node.js / npm**: Instalado y en el PATH.

## Comandos Disponibles

Abre una terminal de PowerShell en la raíz del proyecto y ejecuta:

### 1. Iniciar el Proyecto
Lanza el backend y el frontend en ventanas separadas. Puedes usar el acceso rápido o el comando completo.
```powershell
.\start.ps1
# o
.\manage.ps1 start
```

### 2. Detener el Proyecto
Cierra los procesos que están usando los puertos del backend (8000) y frontend (5173).
```powershell
.\stop.ps1
# o
.\manage.ps1 stop
```

### 3. Inicializar el Proyecto (Primera vez)
Este comando creará el entorno virtual, instalará las dependencias de Python y Node, y preparará la base de datos (migraciones y datos iniciales).
```powershell
.\manage.ps1 init
```

### 4. Reiniciar
Detiene y vuelve a arrancar todo.
```powershell
.\manage.ps1 restart
```

### 5. Ver Estado
Muestra si los servicios están activos o detenidos.
```powershell
.\manage.ps1 status
```

---

## Solución de Problemas

### Error de "Scripts Deshabilitados"
Si PowerShell te da un error diciendo que no se pueden ejecutar scripts, corre este comando una vez en tu terminal como administrador:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Puertos ocupados
Si el script dice que el puerto ya está ocupado pero no ves ninguna ventana, usa `.\stop.ps1` para forzar el cierre de procesos huérfanos.
