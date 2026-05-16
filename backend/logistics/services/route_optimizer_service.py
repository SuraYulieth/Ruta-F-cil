import math
from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from logistics.models import Pedido


PRIORITY_SCORE = {
    'baja': 0,
    'normal': 10,
    'alta': 25,
    'urgente': 40,
}


@dataclass
class GeoPoint:
    lat: float
    lng: float


class RouteOptimizerService:
    """
    First practical optimizer:
    - Filters feasible pending orders by coordinates and capacity.
    - Scores orders by proximity, urgency, priority and cluster convenience.
    - Orders selected stops with nearest neighbor.

    The interface is intentionally provider-agnostic so Google Maps, Mapbox,
    OSRM or OR-Tools can replace individual steps later.
    """

    average_speed_kmh = 28

    def optimize(self, repartidor_id, latitud_inicial, longitud_inicial, pedidos_candidatos=None,
                 capacidad_maxima=None, reglas_negocio=None):
        start = GeoPoint(float(latitud_inicial), float(longitud_inicial))
        capacity = float(capacidad_maxima or 15)
        rules = reglas_negocio or {}
        candidates = self._get_candidates(pedidos_candidatos)

        feasible, discarded = self._filter_feasible(candidates, capacity)
        scored = self._score_orders(feasible, start, capacity, rules)
        selected = self._select_by_capacity(scored, capacity, rules)
        ordered_stops, total_distance = self._nearest_neighbor(start, [item['pedido'] for item in selected])
        duration_mins = self._estimate_duration(total_distance, len(ordered_stops))

        selected_ids = {stop['pedido'].id for stop in ordered_stops}
        discarded.extend(self._discarded_from_scoring(scored, selected_ids))

        return {
            'repartidor_id': repartidor_id,
            'start': {'lat': start.lat, 'lng': start.lng},
            'pedidos_seleccionados': [stop['pedido'] for stop in ordered_stops],
            'orden_entrega': ordered_stops,
            'pedidos_descartados': discarded,
            'distancia_total_km': round(total_distance, 2),
            'duracion_total_mins': duration_mins,
            'capacidad_usada_kg': round(sum(float(stop['pedido'].peso_total_kg or 0) for stop in ordered_stops), 2),
            'geometria': {
                'type': 'LineString',
                'coordinates': [[start.lng, start.lat]] + [
                    [stop['lng'], stop['lat']] for stop in ordered_stops
                ],
            },
            'explicacion': self._build_explanation(
                [{'pedido': stop['pedido']} for stop in ordered_stops],
                total_distance,
                duration_mins,
            ),
        }

    def _get_candidates(self, pedidos_candidatos):
        queryset = Pedido.objects.select_related('cliente', 'aliado').filter(estado='Pendiente')
        if pedidos_candidatos:
            queryset = queryset.filter(id__in=pedidos_candidatos)
        return list(queryset)

    def _filter_feasible(self, candidates, capacity):
        feasible = []
        discarded = []
        for pedido in candidates:
            lat = pedido.cliente.latitud
            lng = pedido.cliente.longitud
            weight = float(pedido.peso_total_kg or 0)
            if lat is None or lng is None:
                discarded.append({
                    'pedido_id': pedido.id,
                    'motivo': 'El pedido no tiene coordenadas de cliente.',
                })
                continue
            if weight > capacity:
                discarded.append({
                    'pedido_id': pedido.id,
                    'motivo': 'El peso del pedido supera la capacidad disponible.',
                })
                continue
            feasible.append(pedido)
        return feasible, discarded

    def _score_orders(self, pedidos, start, capacity, rules):
        if not pedidos:
            return []

        scored = []
        now = timezone.now()
        for pedido in pedidos:
            point = GeoPoint(float(pedido.cliente.latitud), float(pedido.cliente.longitud))
            distance_from_driver = haversine_km(start.lat, start.lng, point.lat, point.lng)
            cluster_distance = self._average_distance_to_orders(pedido, pedidos)
            priority = PRIORITY_SCORE.get(pedido.prioridad, 10)
            delivery_window_score = self._delivery_window_score(pedido, now)
            weight_penalty = (float(pedido.peso_total_kg or 0) / capacity) * 12 if capacity else 0

            score = (
                max(0, 45 - distance_from_driver * 4)
                + max(0, 25 - cluster_distance * 3)
                + priority
                + delivery_window_score
                - weight_penalty
            )
            scored.append({
                'pedido': pedido,
                'score': round(score, 2),
                'distance_from_driver_km': round(distance_from_driver, 2),
                'cluster_distance_km': round(cluster_distance, 2),
                'priority_score': priority,
                'delivery_window_score': delivery_window_score,
            })

        return sorted(scored, key=lambda item: item['score'], reverse=True)

    def _select_by_capacity(self, scored, capacity, rules):
        max_orders = int(rules.get('max_orders', 6))
        selected = []
        used_capacity = 0.0

        for item in scored:
            pedido = item['pedido']
            weight = float(pedido.peso_total_kg or 0)
            if used_capacity + weight <= capacity and len(selected) < max_orders:
                selected.append(item)
                used_capacity += weight

        return selected

    def _nearest_neighbor(self, start, pedidos):
        remaining = list(pedidos)
        current = start
        ordered = []
        total_distance = 0.0

        while remaining:
            next_order = min(
                remaining,
                key=lambda pedido: haversine_km(
                    current.lat,
                    current.lng,
                    float(pedido.cliente.latitud),
                    float(pedido.cliente.longitud),
                ),
            )
            next_point = GeoPoint(float(next_order.cliente.latitud), float(next_order.cliente.longitud))
            leg_distance = haversine_km(current.lat, current.lng, next_point.lat, next_point.lng)
            total_distance += leg_distance
            ordered.append({
                'pedido': next_order,
                'lat': next_point.lat,
                'lng': next_point.lng,
                'distancia_desde_anterior_km': round(leg_distance, 2),
                'tiempo_estimado_desde_anterior_mins': self._estimate_duration(leg_distance, 0),
            })
            current = next_point
            remaining.remove(next_order)

        return ordered, total_distance

    def _average_distance_to_orders(self, pedido, pedidos):
        others = [other for other in pedidos if other.id != pedido.id]
        if not others:
            return 0
        lat = float(pedido.cliente.latitud)
        lng = float(pedido.cliente.longitud)
        distances = [
            haversine_km(lat, lng, float(other.cliente.latitud), float(other.cliente.longitud))
            for other in others
            if other.cliente.latitud is not None and other.cliente.longitud is not None
        ]
        return sum(distances) / len(distances) if distances else 0

    def _delivery_window_score(self, pedido, now):
        if not pedido.ventana_entrega_fin:
            return 0
        minutes_left = (pedido.ventana_entrega_fin - now).total_seconds() / 60
        if minutes_left < 0:
            return -30
        if minutes_left <= 45:
            return 25
        if minutes_left <= 120:
            return 12
        return 4

    def _estimate_duration(self, distance_km, stops_count):
        travel_minutes = (distance_km / self.average_speed_kmh) * 60 if self.average_speed_kmh else 0
        service_minutes = stops_count * 4
        return int(math.ceil(travel_minutes + service_minutes))

    def _discarded_from_scoring(self, scored, selected_ids):
        discarded = []
        for item in scored:
            pedido = item['pedido']
            if pedido.id not in selected_ids:
                discarded.append({
                    'pedido_id': pedido.id,
                    'motivo': 'No fue seleccionado por capacidad, prioridad o conveniencia geográfica.',
                    'score': item['score'],
                })
        return discarded

    def _build_explanation(self, selected, total_distance, duration_mins):
        if not selected:
            return 'No se encontraron pedidos pendientes viables con coordenadas y capacidad disponible.'
        order_ids = [item['pedido'].id for item in selected]
        return (
            f"Se seleccionaron los pedidos {order_ids} por mejor combinación de cercanía, "
            f"agrupación geográfica, prioridad y capacidad. Ruta estimada: "
            f"{round(total_distance, 2)} km en {duration_mins} minutos."
        )


def haversine_km(lat1, lon1, lat2, lon2):
    radius_km = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def to_decimal(value):
    return Decimal(str(round(float(value), 8)))
