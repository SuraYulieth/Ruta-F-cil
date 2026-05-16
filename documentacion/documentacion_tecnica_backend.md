# Documentación Técnica - Backend Ruta Fácil

## 1. Información General
El backend del proyecto "Ruta Fácil" está desarrollado bajo una arquitectura RESTful robusta orientada a proveer servicios al frontend en React, delegando toda la complejidad transaccional y de asignación (lógica de negocio) al servidor.

- **Lenguaje:** Python 3
- **Framework Principal:** Django 6.0
- **Framework API:** Django REST Framework (DRF)
- **Base de Datos:** SQLite (`db.sqlite3`)
- **Módulo Principal:** `logistics`

---

## 2. Configuración e Instalación

Para ejecutar este entorno en local, se deben seguir los siguientes pasos:

1. **Activar Entorno Virtual:**
   ```bash
   # En la carpeta backend/
   .\venv\Scripts\activate
   ```

2. **Instalar Dependencias:**
   ```bash
   pip install django djangorestframework django-cors-headers
   ```

3. **Ejecutar Migraciones:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Sembrar Datos Iniciales (Mock Data):**
   ```bash
   python seed.py
   ```

5. **Levantar el Servidor:**
   ```bash
   python manage.py runserver
   ```
   El backend correrá por defecto en `http://localhost:8000/`.

---

## 3. Arquitectura de Datos (Modelos)

El motor principal reside en el modelo `CustomUser` y su relación estricta con el ecosistema de distribución.

- **CustomUser (Control de Acceso - RBAC):** 
  Extiende el usuario nativo de Django (`AbstractUser`). Centraliza credenciales y roles.
  - Campos clave: `role` (admin, aliado, driver), `nombre`, `estado`, `ubicacion`.
  
- **Cliente:** 
  Almacena la información de los usuarios finales (compradores).
  - Campos clave: `nombre`, `direccion`, `latitud`, `longitud`.
  
- **Pedido:** 
  El núcleo transaccional. Vincula a un `Cliente` (obligatorio) y dinámicamente a un `CustomUser` (repartidor).
  - Campos clave: `cliente`, `repartidor`, `estado` (Pendiente, Asignado, En ruta, Entregado, Cancelado).

---

## 4. Endpoints de la API (Rutas RESTful)

Todas las rutas están pre-fijadas con `/api/`.

### 4.1. Autenticación
- **Ruta:** `POST /api/login/`
- **Descripción:** Valida credenciales y devuelve el perfil completo adaptado a la necesidad del Frontend.
- **Body Esperado:**
  ```json
  { "username": "admin", "password": "123" }
  ```
- **Respuesta (200 OK):**
  ```json
  {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "name": "Super Admin",
    "status": "Disponible",
    "location": "Sin ubicación"
  }
  ```

### 4.2. Gestión de Usuarios
- **Ruta:** `GET /api/users/`
- **Descripción:** Lista todos los usuarios registrados (repartidores y administradores), aplanando el modelo para que concuerde con React.

### 4.3. Gestión de Pedidos
- **Ruta:** `GET /api/pedidos/`
- **Descripción:** Lista todas las rutas y pedidos. El serializador transforma inteligentemente el ID del cliente en `customer` y su dirección en `destination`.

- **Ruta:** `POST /api/pedidos/`
- **Descripción:** Permite al frontend crear un pedido enviando solo texto plano. Django buscará/creará automáticamente al `Cliente` para enlazarlo y mantener la integridad relacional.
- **Body Esperado:**
  ```json
  {
    "customer": "Restaurante El Buen Sabor",
    "destination": "Calle 45 # 12-34"
  }
  ```

- **Ruta:** `PATCH /api/pedidos/{id}/`
- **Descripción:** Actualización parcial. Utilizado por el driver para cambiar el estado a "En ruta" o "Entregado".

### 4.4. Algoritmia de Asignación
- **Ruta:** `POST /api/pedidos/asignar_automatico/`
- **Descripción:** Endpoint crítico de negocio. Ejecuta un algoritmo de emparejamiento (Greedy) evaluando a los pedidos `Pendientes` y los repartidores `Disponibles`.
- **Complejidad:** $O(M \times N)$
- **Acción Oculta:** Muta el estado del pedido a `Asignado` y bloquea temporalmente al repartidor mutando su estado a `Ocupado`.

---

## 5. Decisiones de Diseño y Seguridad (Security by Design)

- **Prevención de Overfetching:** Se sobrescribieron los métodos nativos de DRF (`serializers.py` y `views.py`) para formatear la respuesta HTTP en la misma estructura estricta del context de React. 
- **RBAC Seguro:** Se abandonó la relación endeble con el `User` por defecto y se inyectó una entidad global con roles validados desde la Base de Datos.
