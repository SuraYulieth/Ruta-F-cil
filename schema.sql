-- ==========================================
-- Esquema de Base de Datos - Ruta Fácil
-- ==========================================
-- DBMS: SQLite
-- Descripción: Script de creación de tablas
-- para el manejo de asignación de pedidos, 
-- bodegas/tiendas aliadas y repartidores.
-- ==========================================

-- Tabla de Usuarios (Ciberseguridad básica, Auth)
CREATE TABLE IF NOT EXISTS Usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario VARCHAR(50) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL, -- Se almacenará el hash de bcrypt/argon2
    rol VARCHAR(20) NOT NULL CHECK(rol IN ('admin', 'aliado', 'repartidor')),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Aliados (Tiendas o Bodegas)
CREATE TABLE IF NOT EXISTS Aliados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    latitud DECIMAL(10, 8) NOT NULL,
    longitud DECIMAL(11, 8) NOT NULL,
    estado VARCHAR(20) DEFAULT 'activo' CHECK(estado IN ('activo', 'inactivo')),
    FOREIGN KEY (usuario_id) REFERENCES Usuarios(id) ON DELETE CASCADE
);

-- Tabla de Repartidores
CREATE TABLE IF NOT EXISTS Repartidores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    latitud_actual DECIMAL(10, 8),
    longitud_actual DECIMAL(11, 8),
    estado VARCHAR(20) DEFAULT 'disponible' CHECK(estado IN ('disponible', 'ocupado', 'desconectado')),
    FOREIGN KEY (usuario_id) REFERENCES Usuarios(id) ON DELETE CASCADE
);

-- Tabla de Clientes
CREATE TABLE IF NOT EXISTS Clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(100),
    telefono VARCHAR(20) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    latitud DECIMAL(10, 8) NOT NULL,
    longitud DECIMAL(11, 8) NOT NULL
);

-- Tabla de Pedidos
CREATE TABLE IF NOT EXISTS Pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    aliado_id INTEGER, -- Puede ser Nulo hasta que el sistema asigne la bodega más cercana
    repartidor_id INTEGER,  -- Asignado por el algoritmo
    descripcion TEXT NOT NULL,
    estado VARCHAR(30) DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'asignado', 'en_transito', 'entregado', 'cancelado')),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega DATETIME,
    FOREIGN KEY (cliente_id) REFERENCES Clientes(id),
    FOREIGN KEY (aliado_id) REFERENCES Aliados(id),
    FOREIGN KEY (repartidor_id) REFERENCES Repartidores(id)
);

-- Tabla de Rutas (Histórico y métricas de viaje)
CREATE TABLE IF NOT EXISTS Rutas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL,
    repartidor_id INTEGER NOT NULL,
    tiempo_estimado_mins INTEGER,
    distancia_km DECIMAL(6, 2),
    estado_ruta VARCHAR(20) DEFAULT 'calculada' CHECK(estado_ruta IN ('calculada', 'completada', 'fallida')),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pedido_id) REFERENCES Pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (repartidor_id) REFERENCES Repartidores(id) ON DELETE CASCADE
);

-- Índices para mejorar la velocidad en la búsqueda por lat/long y estado
CREATE INDEX IF NOT EXISTS idx_aliados_ubicacion ON Aliados(latitud, longitud);
CREATE INDEX IF NOT EXISTS idx_repartidores_ubicacion ON Repartidores(latitud_actual, longitud_actual);
CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON Pedidos(estado);
