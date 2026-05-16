import math
from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from logistics.models import Aliado, Pedido, Repartidor


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
    Optimizer inicial, entendible y reemplazable:
    - Escoge repartidor disponible si no viene uno explicito.
    - Asigna bodega/aliado cercano cuando el pedido no tiene aliado.
    - Filtra pedidos inviables por coordenadas/capacidad.
    - Hace scoring logistico y ordena entregas con nearest neighbor.
    """

    average_speed_kmh = 28

    def optimize(self, repartidor_id=None, latitud_inicial=None, longitud_inicial=None,
                 pedidos_candidatos=None, capacidad_maxima=None, reglas_negocio=None):
        rules = reglas_negocio or {}
        candidates = self._get_candidates(pedidos_candidatos)
        driver_profile = self._resolve_driver(repartidor_id, latitud_inicial, longitud_inicial, candidates)
        start = driver_profile['start']
        capacity = float(capacidad_maxima or driver_profile['capacity'] or 15)
        selected_warehouse, warehouse_notes = self._assign_nearest_warehouses(candidates)

        feasible, discarded = self._filter_feasible(candidates, capacity)
        discarded.extend(warehouse_notes)
        scored = self._score_orders(feasible, start, capacity, rules)
        selected = self._select_by_capacity(scored, capacity, rules)
        ordered_stops, total_distance = self._nearest_neighbor(start, [item['pedido'] for item in selected])
        duration_mins = self._estimate_duration(total_distance, len(ordered_stops))

        selected_ids = {stop['pedido'].id for stop in ordered_stops}
        discarded.extend(self._discarded_from_scoring(scored, selected_ids))

        return {
            'repartidor_id': driver_profile['repartidor_id'],
            'repartidor_nombre': driver_profile.get('name'),
            'repartidor_motivo': driver_profile.get('motivo'),
            'aliado_id': selected_warehouse.id if selected_warehouse else None,
            'aliado_nombre': selected_warehouse.user.nombre if selected_warehouse else None,
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
                driver_profile,
                selected_warehouse,
            ),
            'scoring': [
                {
                    'pedido_id': item['pedido'].id,
                    'score': item['score'],
                    'distancia_repartidor_km': item['distance_from_driver_km'],
                    'distancia_cluster_km': item['cluster_distance_km'],
                    'prioridad': item['pedido'].prioridad,
                }
                for item in scored
            ],
        }

    def _get_candidates(self, pedidos_candidatos):
        queryset = Pedido.objects.select_related('cliente', 'aliado__user').filter(estado='Pendiente')
        if pedidos_candidatos:
            queryset = queryset.filter(id__in=pedidos_candidatos)
        return list(queryset)

    def _resolve_driver(self, repartidor_id, latitud_inicial, longitud_inicial, candidates):
        if repartidor_id:
            profile = Repartidor.objects.select_related('user').filter(user_id=repartidor_id).first()
            if profile:
                start = self._driver_start(profile, latitud_inicial, longitud_inicial)
                return {
                    'repartidor_id': profile.user_id,
                    'name': profile.user.nombre,
                    'start': start,
                    'capacity': float(profile.capacidad_maxima_kg or 15),
                    'motivo': 'Repartidor indicado por la solicitud.',
                }
            return {
                'repartidor_id': repartidor_id,
                'name': None,
                'start': GeoPoint(float(latitud_inicial or 0), float(longitud_inicial or 0)),
                'capacity': 15,
                'motivo': 'No se encontro perfil Repartidor; se usaron coordenadas de la solicitud.',
            }

        drivers = list(
            Repartidor.objects.select_related('user')
            .filter(
                user__role='driver',
                user__estado='Disponible',
                latitud_actual__isnull=False,
                longitud_actual__isnull=False,
            )
        )
        if drivers and candidates:
            centroid = self._orders_centroid(candidates)
            best_driver = min(
                drivers,
                key=lambda driver: haversine_km(
                    float(driver.latitud_actual),
                    float(driver.longitud_actual),
                    centroid.lat,
                    centroid.lng,
                ),
            )
            return {
                'repartidor_id': best_driver.user_id,
                'name': best_driver.user.nombre,
                'start': GeoPoint(float(best_driver.latitud_actual), float(best_driver.longitud_actual)),
                'capacity': float(best_driver.capacidad_maxima_kg or 15),
                'motivo': 'Repartidor disponible mas cercano al centro de los pedidos pendientes.',
            }

        return {
            'repartidor_id': None,
            'name': None,
            'start': GeoPoint(float(latitud_inicial or 0), float(longitud_inicial or 0)),
            'capacity': 15,
            'motivo': 'No hay repartidores disponibles con coordenadas.',
        }

    def _driver_start(self, profile, latitud_inicial, longitud_inicial):
        lat = latitud_inicial if latitud_inicial is not None else profile.latitud_actual
        lng = longitud_inicial if longitud_inicial is not None else profile.longitud_actual
        return GeoPoint(float(lat or 0), float(lng or 0))

    def _orders_centroid(self, candidates):
        points = [
            (float(order.cliente.latitud), float(order.cliente.longitud))
            for order in candidates
            if order.cliente.latitud is not None and order.cliente.longitud is not None
        ]
        if not points:
            return GeoPoint(0, 0)
        return GeoPoint(
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
        )

    def _assign_nearest_warehouses(self, candidates):
        warehouses = list(
            Aliado.objects.select_related('user')
            .filter(latitud__isnull=False, longitud__isnull=False)
        )
        if not warehouses:
            return None, [{'pedido_id': None, 'motivo': 'No hay bodegas/aliados con coordenadas registradas.'}]

        selected_counts = {}
        for pedido in candidates:
            if pedido.aliado_id:
                selected_counts[pedido.aliado_id] = selected_counts.get(pedido.aliado_id, 0) + 1
                continue
            if pedido.cliente.latitud is None or pedido.cliente.longitud is None:
                continue

            nearest = min(
                warehouses,
                key=lambda warehouse: haversine_km(
                    float(pedido.cliente.latitud),
                    float(pedido.cliente.longitud),
                    float(warehouse.latitud),
                    float(warehouse.longitud),
                ),
            )
            pedido.aliado = nearest
            selected_counts[nearest.id] = selected_counts.get(nearest.id, 0) + 1

        selected_id = max(selected_counts, key=selected_counts.get) if selected_counts else None
        selected = next((warehouse for warehouse in warehouses if warehouse.id == selected_id), None)
        return selected, []

    def _filter_feasible(self, candidates, capacity):
        feasible = []
        discarded = []
        for pedido in candidates:
            lat = pedido.cliente.latitud
            lng = pedido.cliente.longitud
            weight = float(pedido.peso_total_kg or 0)
            if lat is None or lng is None:
                discarded.append({'pedido_id': pedido.id, 'motivo': 'El pedido no tiene coordenadas de cliente.'})
                continue
            if weight > capacity:
                discarded.append({'pedido_id': pedido.id, 'motivo': 'El peso del pedido supera la capacidad disponible.'})
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
            warehouse_bonus = 8 if pedido.aliado_id else 0

            score = (
                max(0, 45 - distance_from_driver * 4)
                + max(0, 25 - cluster_distance * 3)
                + priority
                + delivery_window_score
                + warehouse_bonus
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
                    'motivo': 'No fue seleccionado por capacidad, prioridad o conveniencia geografica.',
                    'score': item['score'],
                })
        return discarded

    def _build_explanation(self, selected, total_distance, duration_mins, driver_profile=None, warehouse=None):
        if not selected:
            return 'No se encontraron pedidos pendientes viables con coordenadas y capacidad disponible.'
        order_ids = [item['pedido'].id for item in selected]
        driver_text = ''
        if driver_profile:
            driver_text = f" Repartidor: {driver_profile.get('name') or driver_profile.get('repartidor_id')} ({driver_profile.get('motivo')})."
        warehouse_text = f" Bodega base: {warehouse.user.nombre}." if warehouse else ''
        return (
            f"Se seleccionaron los pedidos {order_ids} por mejor combinacion de cercania, "
            f"agrupacion geografica, prioridad, bodega cercana y capacidad. Ruta estimada: "
            f"{round(total_distance, 2)} km en {duration_mins} minutos."
            f"{driver_text}{warehouse_text}"
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
