"""
Helpers geoespaciales para optimización de rutas.

Incluye funciones para:
- Cálculo de distancias Haversine
- Verificación de puntos dentro de radio
- Clustering de pedidos por proximidad
- División automática de rutas por radio
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional

from logistics.config import MAX_ROUTE_RADIUS_KM, RADIUS_TOLERANCE_KM


@dataclass
class GeoPoint:
    """Punto geográfico con latitud y longitud."""
    lat: float
    lng: float

    @property
    def coords(self) -> Tuple[float, float]:
        """Retorna tupla (lat, lng)."""
        return (self.lat, self.lng)

    def __str__(self):
        return f"({self.lat:.6f}, {self.lng:.6f})"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia entre dos puntos usando la fórmula de Haversine.

    Args:
        lat1, lon1: Latitud y longitud del primer punto
        lat2, lon2: Latitud y longitud del segundo punto

    Returns:
        Distancia en kilómetros
    """
    radius_km = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia entre dos puntos en metros.

    Returns:
        Distancia en metros
    """
    return haversine_km(lat1, lon1, lat2, lon2) * 1000


def is_within_radius(
    origin_lat: float,
    origin_lng: float,
    target_lat: float,
    target_lng: float,
    max_radius_km: Optional[float] = None,
) -> bool:
    """
    Verifica si un punto objetivo está dentro del radio máximo permitido desde el origen.

    Args:
        origin_lat, origin_lng: Coordenadas del punto de origen
        target_lat, target_lng: Coordenadas del punto objetivo
        max_radius_km: Radio máximo en km (por defecto usa MAX_ROUTE_RADIUS_KM)

    Returns:
        True si el punto está dentro del radio, False en caso contrario
    """
    if max_radius_km is None:
        max_radius_km = MAX_ROUTE_RADIUS_KM

    distance_km = haversine_km(origin_lat, origin_lng, target_lat, target_lng)
    return distance_km <= (max_radius_km + RADIUS_TOLERANCE_KM)


def get_distance_km(
    origin_lat: float,
    origin_lng: float,
    target_lat: float,
    target_lng: float,
) -> float:
    """
    Obtiene la distancia en km entre dos puntos.
    """
    return haversine_km(origin_lat, origin_lng, target_lat, target_lng)


def calculate_centroid(points: List[Tuple[float, float]]) -> GeoPoint:
    """
    Calcula el centroide (centro geométrico) de una lista de puntos.

    Args:
        points: Lista de tuplas (lat, lng)

    Returns:
        GeoPoint con las coordenadas del centroide
    """
    if not points:
        return GeoPoint(0, 0)

    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]

    return GeoPoint(
        lat=sum(lats) / len(lats),
        lng=sum(lngs) / len(lngs),
    )


def cluster_by_radius(
    items: List,
    get_coords_fn,
    center_lat: float,
    center_lng: float,
    max_radius_km: Optional[float] = None,
) -> Tuple[List, List]:
    """
    Divide una lista de items en dos grupos: dentro del radio y fuera del radio.

    Args:
        items: Lista de items a clasificar
        get_coords_fn: Función que extrae (lat, lng) de cada item
        center_lat, center_lng: Punto central para medir distancias
        max_radius_km: Radio máximo en km

    Returns:
        Tupla (items_dentro_radio, items_fuera_radio)
    """
    if max_radius_km is None:
        max_radius_km = MAX_ROUTE_RADIUS_KM

    within = []
    outside = []

    for item in items:
        lat, lng = get_coords_fn(item)
        if is_within_radius(center_lat, center_lng, lat, lng, max_radius_km):
            within.append(item)
        else:
            outside.append(item)

    return within, outside


def find_nearest_item(
    target_lat: float,
    target_lng: float,
    items: List,
    get_coords_fn,
) -> Optional[Tuple[float, object]]:
    """
    Encuentra el item más cercano a un punto objetivo.

    Args:
        target_lat, target_lng: Coordenadas del punto objetivo
        items: Lista de items entre los que buscar
        get_coords_fn: Función que extrae (lat, lng) de cada item

    Returns:
        Tupla (distancia_km, item) o None si la lista está vacía
    """
    if not items:
        return None

    min_distance = float('inf')
    nearest = None

    for item in items:
        lat, lng = get_coords_fn(item)
        distance = haversine_km(target_lat, target_lng, lat, lng)
        if distance < min_distance:
            min_distance = distance
            nearest = item

    return (min_distance, nearest) if nearest else None


def multipoint_nearest_neighbor(
    start_lat: float,
    start_lng: float,
    points: List[Tuple[float, float]],
) -> List[Tuple[int, Tuple[float, float], float]]:
    """
    Calcula la ruta óptima usando el algoritmo nearest neighbor desde un punto inicial.

    Args:
        start_lat, start_lng: Coordenadas iniciales
        points: Lista de tuplas (lat, lng) a visitar

    Returns:
        Lista de tuplas (índice_original, (lat, lng), distancia_desde_anterior)
    """
    remaining_indices = list(range(len(points)))
    current_lat, current_lng = start_lat, start_lng
    route = []
    total_distance = 0.0

    while remaining_indices:
        # Encontrar el punto más cercano
        nearest_idx = min(
            remaining_indices,
            key=lambda i: haversine_km(
                current_lat, current_lng, points[i][0], points[i][1]
            ),
        )

        next_point = points[nearest_idx]
        leg_distance = haversine_km(current_lat, current_lng, next_point[0], next_point[1])
        total_distance += leg_distance

        route.append((nearest_idx, next_point, leg_distance))

        current_lat, current_lng = next_point
        remaining_indices.remove(nearest_idx)

    return route


def calculate_bounding_box(
    points: List[Tuple[float, float]],
) -> Tuple[float, float, float, float]:
    """
    Calcula el rectángulo delimitador (bounding box) de una lista de puntos.

    Args:
        points: Lista de tuplas (lat, lng)

    Returns:
        Tupla (min_lat, max_lat, min_lng, max_lng)
    """
    if not points:
        return (0, 0, 0, 0)

    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]

    return (min(lats), max(lats), min(lngs), max(lngs))


def get_route_bounding_circle(
    points: List[Tuple[float, float]],
) -> Tuple[float, float, float]:
    """
    Calcula el círculo delimitador mínimo (aproximado) que contiene todos los puntos.

    Args:
        points: Lista de tuplas (lat, lng)

    Returns:
        Tupla (centro_lat, centro_lng, radio_km)
    """
    if not points:
        return (0, 0, 0)

    center = calculate_centroid(points)
    max_distance = 0.0

    for lat, lng in points:
        distance = haversine_km(center.lat, center.lng, lat, lng)
        if distance > max_distance:
            max_distance = distance

    return (center.lat, center.lng, max_distance)


def is_point_valid(lat: Optional[float], lng: Optional[float]) -> bool:
    """
    Verifica si un punto tiene coordenadas válidas.

    Returns:
        True si las coordenadas son válidas (no None y dentro de rangos válidos)
    """
    if lat is None or lng is None:
        return False
    try:
        lat_float = float(lat)
        lng_float = float(lng)
        return -90 <= lat_float <= 90 and -180 <= lng_float <= 180
    except (ValueError, TypeError):
        return False


def format_coords_for_json(lat: float, lng: float) -> dict:
    """Formatea coordenadas para respuesta JSON."""
    return {"lat": round(lat, 6), "lng": round(lng, 6)}
