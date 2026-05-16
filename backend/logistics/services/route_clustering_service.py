"""
Servicio de clustering y división automática de rutas.

Este servicio maneja la lógica de:
- Dividir pedidos en clusters según el radio máximo permitido
- Asignar clusters a múltiples repartidores
- Gestionar pedidos que no caben en ningún repartidor
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field

from logistics.config import MAX_ROUTE_RADIUS_KM
from logistics.models import Pedido, Repartidor
from logistics.services.geospatial_helpers import (
    haversine_km,
    is_within_radius,
    cluster_by_radius,
    calculate_centroid,
    GeoPoint,
)


@dataclass
class PedidoWithDistance:
    """Pedido con información de distancia."""
    pedido: Pedido
    distance_from_center_km: float
    distance_from_driver_km: float


@dataclass
class RouteCluster:
    """Cluster de pedidos para una ruta única."""
    repartidor_id: Optional[int]
    repartidor_nombre: Optional[str]
    center: GeoPoint
    radius_km: float
    pedidos: List[Pedido] = field(default_factory=list)
    weights_total_kg: float = 0.0
    dentro_radio: bool = True

    def can_add_pedido(self, pedido: Pedido, capacity_left_kg: float) -> bool:
        """Verifica si un pedido puede agregarse a este cluster."""
        peso = float(pedido.peso_total_kg or 0)
        if peso > capacity_left_kg:
            return False
        if not pedido.cliente.latitud or not pedido.cliente.longitud:
            return False
        distance = haversine_km(
            self.center.lat,
            self.center.lng,
            float(pedido.cliente.latitud),
            float(pedido.cliente.longitud),
        )
        return distance <= MAX_ROUTE_RADIUS_KM

    def add_pedido(self, pedido: Pedido) -> None:
        """Agrega un pedido al cluster."""
        self.pedidos.append(pedido)
        self.weights_total_kg += float(pedido.peso_total_kg or 0)

    def get_radius_usage_percent(self) -> float:
        """Retorna el porcentaje del radio usado (basado en pedidos más alejados)."""
        if not self.pedidos:
            return 0.0
        max_distance = 0.0
        for pedido in self.pedidos:
            if pedido.cliente.latitud and pedido.cliente.longitud:
                distance = haversine_km(
                    self.center.lat,
                    self.center.lng,
                    float(pedido.cliente.latitud),
                    float(pedido.cliente.longitud),
                )
                if distance > max_distance:
                    max_distance = distance
        return (max_distance / MAX_ROUTE_RADIUS_KM) * 100 if MAX_ROUTE_RADIUS_KM > 0 else 0


class RouteClusteringService:
    """
    Servicio que divide pedidos en múltiples rutas según el radio máximo permitido.
    """

    def cluster_orders_for_drivers(
        self,
        pedidos: List[Pedido],
        drivers: List[Repartidor],
        start_point: GeoPoint,
        capacity_per_driver: float,
    ) -> Tuple[List[RouteCluster], List[Dict]]:
        """
        Agrupa pedidos en clusters, cada uno asignado a un repartidor disponible.

        Args:
            pedidos: Lista de pedidos a agrupar
            drivers: Lista de repartidores disponibles
            start_point: Punto de inicio (bodega o ubicación central)
            capacity_per_driver: Capacidad en kg de cada repartidor

        Returns:
            Tupla (clusters_creados, pedidos_sin_asignar)
        """
        clusters = []
        pedidos_restantes = list(pedidos)
        drivers_disponibles = list(drivers)
        pedidos_sin_asignar = []

        while pedidos_restantes and drivers_disponibles:
            # Crear nuevo cluster con el siguiente repartidor disponible
            driver = drivers_disponibles.pop(0)
            driver_point = GeoPoint(
                float(driver.latitud_actual or 0),
                float(driver.longitud_actual or 0),
            )

            # Si el repartidor no tiene coordenadas, saltar
            if driver.latitud_actual is None or driver.longitud_actual is None:
                continue

            cluster = RouteCluster(
                repartidor_id=driver.user_id,
                repartidor_nombre=driver.user.nombre,
                center=driver_point,
                radius_km=MAX_ROUTE_RADIUS_KM,
            )

            # Agregar pedidos al cluster
            pedidos_a_procesar = list(pedidos_restantes)
            for pedido in pedidos_a_procesar:
                if cluster.can_add_pedido(pedido, capacity_per_driver - cluster.weights_total_kg):
                    cluster.add_pedido(pedido)
                    pedidos_restantes.remove(pedido)

            clusters.append(cluster)

        # Pedidos restantes no pueden ser asignados a repartidores disponibles
        for pedido in pedidos_restantes:
            pedidos_sin_asignar.append({
                'pedido_id': pedido.id,
                'motivo': f'Ningún repartidor disponible puede cubrirlo dentro del radio de {MAX_ROUTE_RADIUS_KM:.2f} km.',
            })

        return clusters, pedidos_sin_asignar

    def identify_clusters_by_proximity(
        self,
        pedidos: List[Pedido],
        distance_threshold_km: float = MAX_ROUTE_RADIUS_KM,
    ) -> List[List[Pedido]]:
        """
        Identifica clusters naturales de pedidos basados en proximidad.

        Usa un algoritmo simple: comienza con un pedido no visitado,
        agrega todos los cercanos, y repite.

        Args:
            pedidos: Lista de pedidos
            distance_threshold_km: Distancia máxima para considerar cercanos

        Returns:
            Lista de clusters (cada cluster es una lista de pedidos)
        """
        if not pedidos:
            return []

        # Filtrar pedidos sin coordenadas
        pedidos_validos = [
            p for p in pedidos
            if p.cliente.latitud and p.cliente.longitud
        ]

        if not pedidos_validos:
            return []

        clusters = []
        visited = set()

        for i, seed_pedido in enumerate(pedidos_validos):
            if i in visited:
                continue

            cluster = [seed_pedido]
            visited.add(i)

            seed_lat = float(seed_pedido.cliente.latitud)
            seed_lng = float(seed_pedido.cliente.longitud)

            for j, candidate in enumerate(pedidos_validos):
                if j in visited:
                    continue

                candidate_lat = float(candidate.cliente.latitud)
                candidate_lng = float(candidate.cliente.longitud)

                distance = haversine_km(seed_lat, seed_lng, candidate_lat, candidate_lng)
                if distance <= distance_threshold_km:
                    cluster.append(candidate)
                    visited.add(j)

            clusters.append(cluster)

        return clusters

    def assign_cluster_to_driver(
        self,
        cluster_pedidos: List[Pedido],
        drivers_available: List[Repartidor],
        capacity_per_driver: float,
    ) -> Tuple[Optional[Repartidor], List[Dict]]:
        """
        Asigna un cluster de pedidos al repartidor más cercano.

        Args:
            cluster_pedidos: Pedidos del cluster
            drivers_available: Repartidores disponibles
            capacity_per_driver: Capacidad disponible

        Returns:
            Tupla (repartidor_asignado, pedidos_descartados)
        """
        if not cluster_pedidos or not drivers_available:
            return None, []

        # Calcular centro del cluster
        coords = [
            (float(p.cliente.latitud), float(p.cliente.longitud))
            for p in cluster_pedidos
            if p.cliente.latitud and p.cliente.longitud
        ]

        if not coords:
            return None, []

        center = calculate_centroid(coords)

        # Encontrar el repartidor más cercano
        closest_driver = min(
            drivers_available,
            key=lambda d: haversine_km(
                center.lat,
                center.lng,
                float(d.latitud_actual or 0),
                float(d.longitud_actual or 0),
            ),
        )

        # Verificar si el repartidor puede cubrir todos los pedidos dentro del radio
        pedidos_descartados = []
        driver_point = GeoPoint(
            float(closest_driver.latitud_actual or 0),
            float(closest_driver.longitud_actual or 0),
        )

        total_weight = 0.0
        pedidos_validos = []

        for pedido in cluster_pedidos:
            peso = float(pedido.peso_total_kg or 0)

            # Verificar capacidad
            if total_weight + peso > capacity_per_driver:
                pedidos_descartados.append({
                    'pedido_id': pedido.id,
                    'motivo': 'Capacidad insuficiente en el repartidor asignado.',
                })
                continue

            # Verificar radio
            if pedido.cliente.latitud and pedido.cliente.longitud:
                distance = haversine_km(
                    driver_point.lat,
                    driver_point.lng,
                    float(pedido.cliente.latitud),
                    float(pedido.cliente.longitud),
                )
                if distance > MAX_ROUTE_RADIUS_KM:
                    pedidos_descartados.append({
                        'pedido_id': pedido.id,
                        'motivo': f'Pedido a {distance:.2f} km del repartidor, fuera del radio permitido de {MAX_ROUTE_RADIUS_KM:.2f} km.',
                    })
                    continue

            pedidos_validos.append(pedido)
            total_weight += peso

        if not pedidos_validos:
            return None, pedidos_descartados

        return closest_driver, pedidos_descartados

    def split_routes_by_capacity_and_radius(
        self,
        pedidos: List[Pedido],
        drivers: List[Repartidor],
        capacity_per_driver: float,
    ) -> Tuple[List[RouteCluster], List[Dict]]:
        """
        Divide rutas considerando tanto capacidad como radio máximo.

        Esta es la función principal que combina clustering + asignación.

        Args:
            pedidos: Pedidos a procesar
            drivers: Repartidores disponibles
            capacity_per_driver: Capacidad en kg

        Returns:
            Tupla (rutas_creadas, pedidos_no_asignados)
        """
        routes = []
        unassigned = []
        remaining_pedidos = list(pedidos)
        remaining_drivers = list(drivers)

        while remaining_pedidos and remaining_drivers:
            driver = remaining_drivers.pop(0)

            # Si el repartidor no tiene coordenadas, continuar
            if driver.latitud_actual is None or driver.longitud_actual is None:
                continue

            driver_point = GeoPoint(
                float(driver.latitud_actual),
                float(driver.longitud_actual),
            )

            # Crear cluster para este repartidor
            cluster = RouteCluster(
                repartidor_id=driver.user_id,
                repartidor_nombre=driver.user.nombre,
                center=driver_point,
                radius_km=MAX_ROUTE_RADIUS_KM,
            )

            # Agregar pedidos que cumplen radio + capacidad
            pedidos_a_procesar = list(remaining_pedidos)
            capacity_left = capacity_per_driver

            for pedido in pedidos_a_procesar:
                if not pedido.cliente.latitud or not pedido.cliente.longitud:
                    unassigned.append({
                        'pedido_id': pedido.id,
                        'motivo': 'Pedido sin coordenadas de cliente.',
                    })
                    remaining_pedidos.remove(pedido)
                    continue

                peso = float(pedido.peso_total_kg or 0)
                distance = haversine_km(
                    driver_point.lat,
                    driver_point.lng,
                    float(pedido.cliente.latitud),
                    float(pedido.cliente.longitud),
                )

                # Verificar ambas restricciones
                if distance <= MAX_ROUTE_RADIUS_KM and peso <= capacity_left:
                    cluster.add_pedido(pedido)
                    capacity_left -= peso
                    remaining_pedidos.remove(pedido)

            if cluster.pedidos:
                routes.append(cluster)

        # Pedidos restantes sin asignar
        for pedido in remaining_pedidos:
            unassigned.append({
                'pedido_id': pedido.id,
                'motivo': f'No hay repartidores disponibles dentro del radio permitido de {MAX_ROUTE_RADIUS_KM:.2f} km.',
            })

        return routes, unassigned
