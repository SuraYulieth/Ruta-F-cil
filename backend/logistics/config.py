"""
Constantes y configuración de optimización de rutas para Ruta Fácil.

REGLA PRINCIPAL (Mayo 2026):
- Área máxima permitida por ruta: 382 km²
- Radio máximo calculado: √(382/π) ≈ 11.03 km
- Lógica: Un repartidor solo puede tener pedidos dentro de un radio de ~11 km
- Si un pedido excede el radio → se asigna a otro repartidor automáticamente
- Si ningún repartidor cumple la regla → pedido queda marcado como no asignado

MATEMÁTICA:
A = π × r²
382 = π × r²
r = √(382/π) ≈ 11.03 km
"""

import math

# ÁREA Y RADIO DE RUTAS
MAX_ROUTE_AREA_KM2 = 382  # Área máxima permitida en km² (a π×r²)
MAX_ROUTE_RADIUS_KM = math.sqrt(MAX_ROUTE_AREA_KM2 / math.pi)  # ~11.03 km
MAX_ROUTE_RADIUS_METERS = MAX_ROUTE_RADIUS_KM * 1000  # ~11030 metros

# CONFIGURACIÓN DE OPTIMIZACIÓN
DEFAULT_DRIVER_CAPACITY_KG = 15.0  # Capacidad máxima por defecto en kg
DEFAULT_MAX_ORDERS_PER_ROUTE = 6  # Máximo de paradas por ruta
AVERAGE_SPEED_KMH = 28  # Velocidad promedio de transporte urbano
SERVICE_TIME_MINUTES_PER_STOP = 4  # Minutos por parada (recepción, entrega, etc.)

# SCORING DE PRIORIDAD
PRIORITY_SCORE = {
    'baja': 0,
    'normal': 10,
    'alta': 25,
    'urgente': 40,
}

# SCORING DE COMPONENTES (máximo puntaje)
MAX_DISTANCE_SCORE = 45  # Mejor si está más cerca del repartidor
MAX_CLUSTERING_SCORE = 25  # Mejor si está agrupado con otros
PRIORITY_COMPONENT = 40  # Máxima prioridad urgente
DELIVERY_WINDOW_SCORE_MAX = 30  # Mejor si tiene ventana cercana
WAREHOUSE_BONUS = 8  # Bonus si tiene aliado asignado
MAX_WEIGHT_PENALTY = 12  # Penalización máxima por peso

# ALERTAS Y UMBRALES
DURATION_WARNING_MINUTES = 90  # Alerta si la ruta excede 90 minutos
DISTANCE_WARNING_KM = 25  # Alerta si la distancia es muy alta
DELIVERY_WINDOW_WARNING_HOURS = 4  # Alerta si la ventana es menor a 4 horas

# TOLERANCIA PARA CÁLCULOS GEOESPACIALES
RADIUS_TOLERANCE_KM = 0.05  # Tolerancia de 50 metros para cálculos de radio

# MOTIVOS DE DESCARTE (para ser más específicos)
DISCARD_REASONS = {
    'radio': 'Fuera del radio máximo permitido ({radius:.2f} km) desde el punto base.',
    'sin_coordenadas': 'El pedido no tiene coordenadas de cliente.',
    'capacidad': 'El peso del pedido supera la capacidad disponible.',
    'capacidad_total': 'No hay capacidad para agregar más pedidos a esta ruta.',
    'scoring': 'No fue seleccionado por capacidad, prioridad o conveniencia geográfica.',
    'repartidor_radio': 'El repartidor está a más de {radius:.2f} km del pedido.',
    'bodega_radio': 'Ninguna bodega disponible está dentro de {radius:.2f} km del pedido.',
    'sin_repartidor_disponible': 'No hay repartidores disponibles que cumplan con la regla de radio.',
    'sin_repartidor_para_radio': 'Ningún repartidor disponible puede cubrir este pedido dentro del radio permitido.',
}

# FACTORES DE CONFIANZA PARA IA
CONFIDENCE_LEVELS = {
    'alto': 'Todos los pedidos están bien agrupados dentro del radio permitido.',
    'medio': 'Algunos pedidos fueron asignados a múltiples repartidores para cumplir el radio.',
    'bajo': 'Muy pocos pedidos disponibles o fuera del radio permitido en todas las opciones.',
}

# CONFIGURACIÓN LOGÍSTICA
MIN_ORDERS_FOR_CONSOLIDATION = 1  # Mínimo de pedidos para consolidar ruta
CONSOLIDATION_TIME_WINDOW_HOURS = 2  # Esperar máximo 2 horas para consolidar

# RECOMENDACIONES AUTOMÁTICAS
RECOMMENDATION_ACTIONS = {
    'asignar_segunda_ruta': 'Crear una segunda ruta con otro repartidor para pedidos descartados.',
    'esperar_pedidos': 'Esperar más pedidos cercanos antes de asignar la ruta.',
    'completar_datos': 'Completar coordenadas, peso y ventanas de entrega para mejorar precisión.',
    'verificar_capacidad': 'Verificar y actualizar capacidades de repartidores.',
    'revisar_coordenadas': 'Revisar coordenadas de bodegas para mejorar asignación.',
    'añadir_repartidor': 'Se recomienda agregar más repartidores para cubrir pedidos alejados.',
}

# VALORES PARA LOGGING Y DEBUGGING
OPTIMIZER_DEBUG = False  # Cambiar a True para log detallado de optimización
