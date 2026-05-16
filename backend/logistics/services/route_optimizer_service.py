import math
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple, Dict, Optional

from django.utils import timezone

from logistics.models import Aliado, Pedido, Repartidor, Ruta
from logistics.config import (
    MAX_ROUTE_RADIUS_KM,
    MAX_ROUTE_RADIUS_METERS,
    MAX_ROUTE_AREA_KM2,
    DURATION_WARNING_MINUTES,
    DISTANCE_WARNING_KM,
    PRIORITY_SCORE,
    DEFAULT_DRIVER_CAPACITY_KG,
    DEFAULT_MAX_ORDERS_PER_ROUTE,
)
from logistics.services.geospatial_helpers import (
    GeoPoint,
    haversine_km,
    is_within_radius,
    cluster_by_radius,
    calculate_centroid,
    get_route_bounding_circle,
)
from logistics.services.driver_visibility import (
    get_driver_coordinates,
    is_available_state,
    is_driver_available,
    is_driver_user,
)


@dataclass
class GeoPoint:
    lat: float
    lng: float


class RouteOptimizerService:
    """
    Optimizer con soporte para múltiples rutas y restricción de radio máximo.

    REGLA PRINCIPAL:
    - Cada ruta puede cubrir un área máxima de 382 km² (radio ~11 km)
    - Un repartidor no puede tener pedidos fuera de ese radio
    - Si hay pedidos fuera del radio → se crean múltiples rutas con diferentes repartidores
    - Si ningún repartidor cumple → pedidos quedan marcados como no asignados

    FLUJO:
    1. Obtener candidatos y validar coordenadas
    2. Resolver repartidor base (si no viene especificado)
    3. Dividir pedidos por clusters geográficos
    4. Asignar clusters a repartidores disponibles
    5. Aplicar nearest neighbor dentro de cada cluster
    6. Retornar múltiples rutas (una por cluster/repartidor)
    """

    average_speed_kmh = 28

    def optimize(
        self,
        repartidor_id: Optional[int] = None,
        latitud_inicial: Optional[float] = None,
        longitud_inicial: Optional[float] = None,
        pedidos_candidatos: Optional[List[int]] = None,
        capacidad_maxima: Optional[float] = None,
        reglas_negocio: Optional[Dict] = None,
    ) -> Dict:
        """
        Optimiza rutas dividiendo automáticamente por radio máximo permitido.

        Returns:
            {
                'rutas': [ruta1, ruta2, ...],  # Múltiples rutas si es necesario
                'ruta_principal': ruta1,  # La ruta principal (primera)
                'pedidos_seleccionados': [...],  # Todos los pedidos en todas las rutas
                'pedidos_descartados': [...],  # Pedidos no asignados
                'total_rutas': cantidad,
                'metricas': {...}
            }
        """
        rules = reglas_negocio or {}
        candidates = self._get_candidates(pedidos_candidatos)
        
        # Resolver repartidor y punto de inicio
        driver_profile = self._resolve_driver(
            repartidor_id, latitud_inicial, longitud_inicial, candidates
        )
        start = driver_profile['start']
        capacity = float(capacidad_maxima or driver_profile.get('capacity', DEFAULT_DRIVER_CAPACITY_KG))
        
        # Asignar bodega cercana
        selected_warehouse, warehouse_notes = self._assign_nearest_warehouses(candidates)

        if not driver_profile.get('repartidor_id'):
            discarded = [
                {
                    'pedido_id': pedido.id,
                    'motivo': driver_profile.get('motivo') or 'No hay repartidor disponible para recibir pedidos.',
                }
                for pedido in candidates
            ]
            discarded.extend(warehouse_notes)
            return self._create_empty_response(
                driver_profile,
                selected_warehouse,
                discarded,
            )
        
        # Filtrar pedidos factibles por coordenadas y capacidad individual
        feasible, discarded = self._filter_feasible(candidates, capacity)
        discarded.extend(warehouse_notes)
        
        # ===== NUEVA LÓGICA: DIVISIÓN POR RADIO MÁXIMO =====
        if not feasible:
            # Sin pedidos factibles
            return self._create_empty_response(
                driver_profile,
                selected_warehouse,
                discarded,
            )
        
        # Dividir pedidos por radio máximo permitido
        within_radius, outside_radius = cluster_by_radius(
            feasible,
            lambda p: (float(p.cliente.latitud), float(p.cliente.longitud)),
            start.lat,
            start.lng,
            MAX_ROUTE_RADIUS_KM,
        )
        
        # Marcar pedidos fuera del radio como descartados por esta razón
        for pedido in outside_radius:
            distance_km = haversine_km(
                start.lat, start.lng,
                float(pedido.cliente.latitud),
                float(pedido.cliente.longitud),
            )
            discarded.append({
                'pedido_id': pedido.id,
                'motivo': f'Pedido a {distance_km:.2f} km del punto base, fuera del radio máximo permitido de {MAX_ROUTE_RADIUS_KM:.2f} km.',
                'distancia_km': round(distance_km, 2),
            })
        
        # Procesar pedidos dentro del radio
        routes = []
        
        if within_radius:
            # Scoring y selección de pedidos dentro del radio
            scored = self._score_orders(within_radius, start, capacity, rules)
            selected = self._select_by_capacity(scored, capacity, rules)
            
            if selected:
                # Aplicar nearest neighbor
                ordered_stops, total_distance = self._nearest_neighbor(
                    start,
                    [item['pedido'] for item in selected],
                )
                duration_mins = self._estimate_duration(total_distance, len(ordered_stops))
                
                # Crear ruta principal
                route = {
                    'repartidor_id': driver_profile['repartidor_id'],
                    'repartidor_nombre': driver_profile.get('name'),
                    'repartidor_motivo': driver_profile.get('motivo'),
                    'aliado_id': selected_warehouse.id if selected_warehouse else None,
                    'aliado_nombre': selected_warehouse.user.nombre if selected_warehouse else None,
                    'start': {'lat': start.lat, 'lng': start.lng},
                    'pedidos_seleccionados': [stop['pedido'] for stop in ordered_stops],
                    'orden_entrega': ordered_stops,
                    'distancia_total_km': round(total_distance, 2),
                    'duracion_total_mins': duration_mins,
                    'capacidad_usada_kg': round(
                        sum(float(stop['pedido'].peso_total_kg or 0) for stop in ordered_stops), 2
                    ),
                    'geometria': {
                        'type': 'LineString',
                        'coordinates': [[start.lng, start.lat]] + [
                            [stop['lng'], stop['lat']] for stop in ordered_stops
                        ],
                    },
                    'radio_permitido_km': MAX_ROUTE_RADIUS_KM,
                    'radio_permitido_m2': MAX_ROUTE_AREA_KM2,
                    'dentro_radio_permitido': True,
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
                
                # Agregar pedidos descartados por scoring
                selected_ids = {stop['pedido'].id for stop in ordered_stops}
                route['pedidos_descartados_por_scoring'] = self._discarded_from_scoring(
                    scored, selected_ids
                )
                
                routes.append(route)
        
        # ===== FIN NUEVA LÓGICA =====
        
        # Construir explicación
        all_selected = []
        for route in routes:
            all_selected.extend(route['pedidos_seleccionados'])
        
        explicacion = self._build_explanation(
            [{'pedido': p} for p in all_selected],
            sum(r['distancia_total_km'] for r in routes),
            sum(r['duracion_total_mins'] for r in routes),
            driver_profile,
            selected_warehouse,
            len(routes),
        )
        primary_route = routes[0] if routes else None
        
        # Respuesta consolidada
        return {
            'rutas': routes,
            'ruta_principal': primary_route,
            'repartidor_id': primary_route.get('repartidor_id') if primary_route else driver_profile.get('repartidor_id'),
            'repartidor_nombre': primary_route.get('repartidor_nombre') if primary_route else driver_profile.get('name'),
            'repartidor_motivo': primary_route.get('repartidor_motivo') if primary_route else driver_profile.get('motivo'),
            'aliado_id': primary_route.get('aliado_id') if primary_route else (selected_warehouse.id if selected_warehouse else None),
            'aliado_nombre': primary_route.get('aliado_nombre') if primary_route else (selected_warehouse.user.nombre if selected_warehouse else None),
            'start': primary_route.get('start') if primary_route else {'lat': start.lat, 'lng': start.lng},
            'orden_entrega': primary_route.get('orden_entrega', []) if primary_route else [],
            'geometria': primary_route.get('geometria') if primary_route else {'type': 'LineString', 'coordinates': [[start.lng, start.lat]]},
            'pedidos_seleccionados': all_selected,
            'pedidos_descartados': discarded,
            'total_rutas': len(routes),
            'radio_permitido_km': MAX_ROUTE_RADIUS_KM,
            'radio_permitido_m2': MAX_ROUTE_AREA_KM2,
            'distancia_total_km': round(sum(r['distancia_total_km'] for r in routes), 2),
            'duracion_total_mins': sum(r['duracion_total_mins'] for r in routes),
            'capacidad_usada_kg': round(primary_route.get('capacidad_usada_kg', 0), 2) if primary_route else 0,
            'capacidad_total_usada_kg': round(
                sum(r['capacidad_usada_kg'] for r in routes), 2
            ),
            'explicacion': explicacion,
            'metricas': {
                'total_pedidos_candidatos': len(candidates),
                'pedidos_factibles': len(feasible),
                'pedidos_dentro_radio': len(within_radius),
                'pedidos_fuera_radio': len(outside_radius),
                'pedidos_seleccionados': len(all_selected),
                'pedidos_descartados': len(discarded),
                'rutas_creadas': len(routes),
            }
        }

    def _create_empty_response(self, driver_profile: Dict, warehouse: Optional[Aliado], discarded: List) -> Dict:
        """Crea respuesta vacía cuando no hay pedidos factibles."""
        start = driver_profile['start']
        return {
            'rutas': [],
            'ruta_principal': None,
            'repartidor_id': driver_profile.get('repartidor_id'),
            'repartidor_nombre': driver_profile.get('name'),
            'repartidor_motivo': driver_profile.get('motivo'),
            'aliado_id': warehouse.id if warehouse else None,
            'aliado_nombre': warehouse.user.nombre if warehouse else None,
            'start': {'lat': start.lat, 'lng': start.lng},
            'orden_entrega': [],
            'geometria': {'type': 'LineString', 'coordinates': [[start.lng, start.lat]]},
            'pedidos_seleccionados': [],
            'pedidos_descartados': discarded,
            'total_rutas': 0,
            'radio_permitido_km': MAX_ROUTE_RADIUS_KM,
            'radio_permitido_m2': MAX_ROUTE_AREA_KM2,
            'distancia_total_km': 0,
            'duracion_total_mins': 0,
            'capacidad_usada_kg': 0,
            'capacidad_total_usada_kg': 0,
            'explicacion': 'No se encontraron pedidos pendientes viables con coordenadas y capacidad disponible.',
            'metricas': {
                'total_pedidos_candidatos': 0,
                'pedidos_factibles': 0,
                'pedidos_dentro_radio': 0,
                'pedidos_fuera_radio': 0,
                'pedidos_seleccionados': 0,
                'pedidos_descartados': len(discarded),
                'rutas_creadas': 0,
            }
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
                if not is_driver_available(profile):
                    return {
                        'repartidor_id': None,
                        'name': profile.user.nombre,
                        'start': GeoPoint(float(latitud_inicial or 0), float(longitud_inicial or 0)),
                        'capacity': DEFAULT_DRIVER_CAPACITY_KG,
                        'motivo': 'El repartidor indicado esta deshabilitado o no disponible.',
                    }
                start = self._driver_start(profile, latitud_inicial, longitud_inicial)
                return {
                    'repartidor_id': profile.user_id,
                    'name': profile.user.nombre,
                    'start': start,
                    'capacity': float(profile.capacidad_maxima_kg or DEFAULT_DRIVER_CAPACITY_KG),
                    'motivo': 'Repartidor indicado por la solicitud.',
                }
            return {
                'repartidor_id': repartidor_id,
                'name': None,
                'start': GeoPoint(float(latitud_inicial or 0), float(longitud_inicial or 0)),
                'capacity': DEFAULT_DRIVER_CAPACITY_KG,
                'motivo': 'No se encontró perfil Repartidor; se usaron coordenadas de la solicitud.',
            }

        drivers = [
            driver
            for driver in Repartidor.objects.select_related('user').all()
            if is_driver_available(driver) and self._get_driver_coordinates(driver) is not None
        ]
        if drivers and candidates:
            centroid = self._orders_centroid(candidates)
            best_driver = min(
                drivers,
                key=lambda driver: haversine_km(
                    self._get_driver_coordinates(driver)[0],
                    self._get_driver_coordinates(driver)[1],
                    centroid.lat,
                    centroid.lng,
                ),
            )
            best_coords = self._get_driver_coordinates(best_driver)
            return {
                'repartidor_id': best_driver.user_id,
                'name': best_driver.user.nombre,
                'start': GeoPoint(best_coords[0], best_coords[1]),
                'capacity': float(best_driver.capacidad_maxima_kg or DEFAULT_DRIVER_CAPACITY_KG),
                'motivo': 'Repartidor disponible más cercano al centro de los pedidos pendientes.',
            }

        return {
            'repartidor_id': None,
            'name': None,
            'start': GeoPoint(float(latitud_inicial or 0), float(longitud_inicial or 0)),
            'capacity': DEFAULT_DRIVER_CAPACITY_KG,
            'motivo': 'No hay repartidores disponibles con coordenadas.',
        }

    def _driver_start(self, profile, latitud_inicial, longitud_inicial):
        if latitud_inicial is not None and longitud_inicial is not None:
            lat, lng = latitud_inicial, longitud_inicial
        else:
            coords = self._get_driver_coordinates(profile)
            if coords is None:
                raise ValueError(f'Repartidor {profile.user.nombre} no tiene coordenadas válidas.')
            lat, lng = coords
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
        max_orders = int(rules.get('max_orders', DEFAULT_MAX_ORDERS_PER_ROUTE))
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
        from logistics.config import AVERAGE_SPEED_KMH, SERVICE_TIME_MINUTES_PER_STOP
        travel_minutes = (distance_km / AVERAGE_SPEED_KMH) * 60 if AVERAGE_SPEED_KMH else 0
        service_minutes = stops_count * SERVICE_TIME_MINUTES_PER_STOP
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

    def _build_explanation(self, selected, total_distance, duration_mins, driver_profile=None, warehouse=None, num_routes=1):
        if not selected:
            return 'No se encontraron pedidos pendientes viables con coordenadas y capacidad disponible.'
        
        order_ids = [item['pedido'].id for item in selected]
        driver_text = ''
        if driver_profile:
            driver_text = f" Repartidor: {driver_profile.get('name') or driver_profile.get('repartidor_id')} ({driver_profile.get('motivo')})."
        warehouse_text = f" Bodega base: {warehouse.user.nombre}." if warehouse else ''
        
        routes_text = ""
        if num_routes > 1:
            routes_text = f" Se crearon {num_routes} rutas para respetar el radio máximo permitido de {MAX_ROUTE_RADIUS_KM:.2f} km."
        
        return (
            f"Se seleccionaron los pedidos {order_ids} por mejor combinación de cercanía, "
            f"agrupación geográfica, prioridad, bodega cercana y capacidad. Ruta estimada: "
            f"{round(total_distance, 2)} km en {duration_mins} minutos."
            f"{driver_text}{warehouse_text}{routes_text}"
        )

    def optimize_all_pending_orders(
        self,
        repartidor_id: Optional[int] = None,
        latitud_inicial: Optional[float] = None,
        longitud_inicial: Optional[float] = None,
        pedidos_candidatos: Optional[List[int]] = None,
        capacidad_maxima: Optional[float] = None,
        reglas_negocio: Optional[Dict] = None,
        max_duration_mins: Optional[float] = None,
        max_area_km2: Optional[float] = None,
        max_distance_km: Optional[float] = None,
    ) -> Dict:
        rules = dict(reglas_negocio or {})
        if max_duration_mins is not None:
            rules['max_duration_mins'] = max_duration_mins
        if max_area_km2 is not None:
            rules['max_area_km2'] = max_area_km2
        if max_distance_km is not None:
            rules['max_distance_km'] = max_distance_km

        candidates = self._get_candidates(pedidos_candidatos)
        driver_diagnostics = self._build_driver_diagnostics(candidates)
        drivers = self._get_available_driver_profiles(repartidor_id, latitud_inicial, longitud_inicial)

        discarded = []
        if not candidates:
            return self._create_multi_empty_response(discarded, driver_diagnostics=driver_diagnostics)

        if not drivers:
            for pedido in candidates:
                discarded.append(self._format_unassigned_order(
                    pedido,
                    None,
                    'No hay repartidores disponibles con coordenadas.',
                ))
            return self._create_multi_empty_response(
                discarded,
                total_candidates=len(candidates),
                driver_diagnostics=driver_diagnostics,
            )

        max_capacity_limit = float(
            capacidad_maxima
            if capacidad_maxima is not None
            else max(driver['capacity'] for driver in drivers)
        )

        valid_candidates = []
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
            if weight > max_capacity_limit:
                discarded.append({
                    'pedido_id': pedido.id,
                    'motivo': 'El peso del pedido supera la capacidad disponible.',
                })
                continue
            valid_candidates.append(pedido)

        if not valid_candidates:
            return self._create_multi_empty_response(
                discarded,
                total_candidates=len(candidates),
                driver_diagnostics=driver_diagnostics,
            )

        remaining = list(valid_candidates)
        routes = []
        used_driver_ids = set()
        preferred_driver_id = repartidor_id

        while remaining:
            driver_candidates = self._ordered_driver_candidates(drivers, remaining, used_driver_ids, preferred_driver_id)
            if not driver_candidates:
                break

            route_created = False
            for driver in driver_candidates:
                if driver['repartidor_id'] in used_driver_ids:
                    continue

                route = self._build_route_for_driver(
                    driver=driver,
                    remaining_orders=remaining,
                    capacity_limit=max_capacity_limit,
                    rules=rules,
                )

                if route:
                    routes.append(route)
                    used_driver_ids.add(driver['repartidor_id'])
                    selected_ids = {pedido.id for pedido in route['pedidos_seleccionados']}
                    remaining = [pedido for pedido in remaining if pedido.id not in selected_ids]
                    preferred_driver_id = None
                    route_created = True
                    break

            if not route_created:
                break

        if remaining:
            for pedido in remaining:
                discarded.append(self._build_unassigned_reason(pedido, drivers, rules, max_capacity_limit))

        all_selected = []
        for route in routes:
            all_selected.extend(route['pedidos_seleccionados'])

        total_distance = round(sum(route['distancia_total_km'] for route in routes), 2)
        total_duration = sum(route['duracion_total_mins'] for route in routes)
        total_capacity = round(sum(route['capacidad_usada_kg'] for route in routes), 2)
        summary = {
            'total_pedidos': len(candidates),
            'pedidos_asignados': len(all_selected),
            'pedidos_no_asignados': len(discarded),
            'rutas_creadas': len(routes),
        }

        return {
            'modo': 'multi_ruta',
            'routes': routes,
            'ruta_principal': routes[0] if routes else None,
            'pedidos_seleccionados': all_selected,
            'pedidos_descartados': discarded,
            'unassigned_orders': discarded,
            'unassigned_summary': self._summarize_unassigned(discarded),
            'driver_diagnostics': driver_diagnostics,
            'total_rutas': len(routes),
            'radio_permitido_km': MAX_ROUTE_RADIUS_KM,
            'radio_permitido_m2': MAX_ROUTE_AREA_KM2,
            'distancia_total_km': total_distance,
            'duracion_total_mins': total_duration,
            'capacidad_total_usada_kg': total_capacity,
            'explicacion': self._build_multi_route_explanation(routes, discarded, summary),
            'summary': summary,
            'metricas': {
                'total_pedidos_candidatos': len(candidates),
                'pedidos_factibles': len(valid_candidates),
                'pedidos_seleccionados': len(all_selected),
                'pedidos_descartados': len(discarded),
                'rutas_creadas': len(routes),
            },
        }

    def _create_multi_empty_response(self, discarded, total_candidates=0, driver_diagnostics=None):
        return {
            'modo': 'multi_ruta',
            'routes': [],
            'ruta_principal': None,
            'pedidos_seleccionados': [],
            'pedidos_descartados': discarded,
            'unassigned_orders': discarded,
            'unassigned_summary': self._summarize_unassigned(discarded),
            'driver_diagnostics': driver_diagnostics or self._empty_driver_diagnostics(),
            'total_rutas': 0,
            'radio_permitido_km': MAX_ROUTE_RADIUS_KM,
            'radio_permitido_m2': MAX_ROUTE_AREA_KM2,
            'distancia_total_km': 0,
            'duracion_total_mins': 0,
            'capacidad_total_usada_kg': 0,
            'explicacion': 'No se encontraron rutas viables para los pedidos pendientes.',
            'summary': {
                'total_pedidos': total_candidates,
                'pedidos_asignados': 0,
                'pedidos_no_asignados': len(discarded),
                'rutas_creadas': 0,
            },
            'metricas': {
                'total_pedidos_candidatos': total_candidates,
                'pedidos_factibles': 0,
                'pedidos_seleccionados': 0,
                'pedidos_descartados': len(discarded),
                'rutas_creadas': 0,
            },
        }

    def _summarize_unassigned(self, unassigned_orders):
        grouped = {}
        for item in unassigned_orders or []:
            motivo = item.get('motivo') or 'Sin motivo especificado.'
            grouped.setdefault(motivo, []).append(item.get('pedido_id'))

        return [
            {
                'motivo': motivo,
                'cantidad': len([pedido_id for pedido_id in pedido_ids if pedido_id is not None]),
                'pedidos': [pedido_id for pedido_id in pedido_ids if pedido_id is not None],
            }
            for motivo, pedido_ids in grouped.items()
        ]

    def _empty_driver_diagnostics(self):
        return {
            'total_repartidores': 0,
            'disponibles': 0,
            'deshabilitados': 0,
            'en_entrega': 0,
            'sin_coordenadas': 0,
            'fuera_de_radio': 0,
            'role_invalido': 0,
            'estado_invalido': 0,
            'aptos_para_optimizar': 0,
            'detalle': [],
        }

    def _build_driver_diagnostics(self, candidates):
        diagnostics = self._empty_driver_diagnostics()
        centroid = self._calculate_orders_centroid(candidates)
        candidate_points = []
        if centroid:
            candidate_points.append((centroid['latitud'], centroid['longitud']))
        diagnostics['coverage_recommendation'] = self._build_coverage_recommendation(candidates, centroid)

        for profile in Repartidor.objects.select_related('user').all():
            user = profile.user
            coords = self._get_driver_coordinates(profile)
            has_active_route = self._driver_has_active_route(user)
            role_valid = is_driver_user(user)
            state_valid = is_available_state(getattr(user, 'estado', None))
            available_flag = profile.disponible is True
            outside_radius = False
            distance_to_centroid = None

            if coords and candidate_points:
                distance_to_centroid = haversine_km(
                    coords[0],
                    coords[1],
                    centroid['latitud'],
                    centroid['longitud'],
                )
                outside_radius = distance_to_centroid > MAX_ROUTE_RADIUS_KM

            if role_valid and available_flag and state_valid:
                diagnostics['disponibles'] += 1
            if not role_valid:
                diagnostics['role_invalido'] += 1
            if not available_flag:
                diagnostics['deshabilitados'] += 1
            if has_active_route:
                diagnostics['en_entrega'] += 1
            if not state_valid:
                diagnostics['estado_invalido'] += 1
            if coords is None:
                diagnostics['sin_coordenadas'] += 1
            if outside_radius:
                diagnostics['fuera_de_radio'] += 1

            apto = (
                role_valid
                and available_flag
                and state_valid
                and coords is not None
                and not has_active_route
                and not outside_radius
            )
            if apto:
                diagnostics['aptos_para_optimizar'] += 1

            diagnostics['detalle'].append({
                'id': user.id,
                'nombre': user.nombre or user.username,
                'estado': user.estado,
                'disponible': profile.disponible,
                'tiene_coordenadas': coords is not None,
                'tiene_ruta_activa': has_active_route,
                'apto': apto,
                'motivo': self._driver_diagnostic_reason(
                    role_valid,
                    available_flag,
                    state_valid,
                    coords is not None,
                    has_active_route,
                    outside_radius,
                ),
                'coordenadas_actuales': (
                    {'latitud': coords[0], 'longitud': coords[1]}
                    if coords else None
                ),
                'coordenadas_recomendadas': (
                    {'latitud': centroid['latitud'], 'longitud': centroid['longitud']}
                    if centroid else None
                ),
                'distancia_al_centro_demanda_km': (
                    round(distance_to_centroid, 2) if distance_to_centroid is not None else None
                ),
                'radio_maximo_km': round(MAX_ROUTE_RADIUS_KM, 2),
                'zona_sugerida': (
                    'Ubicarse cerca del centro de los pedidos pendientes.'
                    if outside_radius else None
                ),
            })

        diagnostics['total_repartidores'] = len(diagnostics['detalle'])
        return diagnostics

    def _calculate_orders_centroid(self, orders):
        valid = []
        for pedido in orders:
            cliente = getattr(pedido, 'cliente', None)
            if cliente and cliente.latitud is not None and cliente.longitud is not None:
                valid.append((float(cliente.latitud), float(cliente.longitud)))

        if not valid:
            return None

        avg_lat = sum(lat for lat, _ in valid) / len(valid)
        avg_lng = sum(lng for _, lng in valid) / len(valid)
        return {
            'latitud': round(avg_lat, 6),
            'longitud': round(avg_lng, 6),
        }

    def _build_coverage_recommendation(self, candidates, centroid):
        if not centroid:
            return {
                'centro_demanda': None,
                'radio_maximo_km': round(MAX_ROUTE_RADIUS_KM, 2),
                'mensaje': 'No hay pedidos pendientes con coordenadas suficientes para calcular un centro de demanda.',
                'google_maps_url': None,
            }

        warehouse = self._select_warehouse_for_orders([
            pedido for pedido in candidates
            if pedido.cliente.latitud is not None and pedido.cliente.longitud is not None
        ])
        warehouse_point = None
        if warehouse and warehouse.latitud is not None and warehouse.longitud is not None:
            warehouse_point = {
                'latitud': float(warehouse.latitud),
                'longitud': float(warehouse.longitud),
                'nombre': warehouse.user.nombre,
            }

        first_order = self._nearest_order_to_centroid(candidates, centroid)

        return {
            'centro_demanda': centroid,
            'radio_maximo_km': round(MAX_ROUTE_RADIUS_KM, 2),
            'mensaje': (
                f'Para tomar estos pedidos, al menos un repartidor disponible debe estar dentro de '
                f'{MAX_ROUTE_RADIUS_KM:.2f} km del centro de demanda. Ubica un repartidor cerca de estas '
                f'coordenadas: latitud {centroid["latitud"]}, longitud {centroid["longitud"]}.'
            ),
            'google_maps_url': f'https://www.google.com/maps?q={centroid["latitud"]},{centroid["longitud"]}',
            'bodega_sugerida': warehouse_point,
            'primer_pedido_cercano': first_order,
        }

    def _nearest_order_to_centroid(self, candidates, centroid):
        valid = [
            pedido for pedido in candidates
            if pedido.cliente.latitud is not None and pedido.cliente.longitud is not None
        ]
        if not valid:
            return None

        nearest = min(
            valid,
            key=lambda pedido: haversine_km(
                centroid['latitud'],
                centroid['longitud'],
                float(pedido.cliente.latitud),
                float(pedido.cliente.longitud),
            ),
        )
        return {
            'pedido_id': nearest.id,
            'latitud': float(nearest.cliente.latitud),
            'longitud': float(nearest.cliente.longitud),
            'direccion': nearest.cliente.direccion,
        }

    def _driver_diagnostic_reason(self, role_valid, available_flag, state_valid, has_coords, has_active_route, outside_radius):
        if not role_valid:
            return 'No tiene un rol valido para reparto.'
        if not available_flag:
            return 'Esta deshabilitado por el repartidor.'
        if has_active_route:
            return 'Esta en entrega actualmente.'
        if not state_valid:
            return 'Su estado operativo no es Disponible.'
        if not has_coords:
            return 'No tiene ubicacion actual registrada.'
        if outside_radius:
            return 'Esta fuera del radio permitido para estos pedidos.'
        return 'Apto para optimizar.'

    def _driver_has_active_route(self, user):
        return Ruta.objects.filter(
            repartidor=user,
            estado_ruta__in=['asignada', 'en_ruta'],
        ).exists()

    def _get_driver_coordinates(self, driver):
        """
        Extrae coordenadas del repartidor desde cualquier campo disponible.
        Intenta en orden: latitud_actual, latitud, latitude.
        """
        return get_driver_coordinates(driver)

    def _get_available_driver_profiles(self, repartidor_id, latitud_inicial, longitud_inicial):
        profiles = []
        # Consultar todos los repartidores, sin filtrar por coordenadas aún
        queryset = Repartidor.objects.select_related('user').all()

        for profile in queryset:
            if not is_driver_available(profile):
                continue
            if self._driver_has_active_route(profile.user):
                continue

            # Verificar que tenga coordenadas válidas usando el helper flexible
            coords = self._get_driver_coordinates(profile)
            if coords is None:
                continue

            profiles.append(self._driver_profile_from_record(profile, None, None))

        if repartidor_id:
            preferred = Repartidor.objects.select_related('user').filter(user_id=repartidor_id).first()
            if (
                preferred
                and is_driver_available(preferred)
                and not self._driver_has_active_route(preferred.user)
                and self._get_driver_coordinates(preferred) is not None
            ):
                preferred_profile = self._driver_profile_from_record(preferred, latitud_inicial, longitud_inicial)
                profiles = [profile for profile in profiles if profile['repartidor_id'] != repartidor_id]
                profiles.insert(0, preferred_profile)

        return profiles

    def _driver_profile_from_record(self, profile, latitud_inicial, longitud_inicial):
        start = self._driver_start(profile, latitud_inicial, longitud_inicial)
        return {
            'repartidor_id': profile.user_id,
            'name': profile.user.nombre,
            'start': start,
            'capacity': float(profile.capacidad_maxima_kg or DEFAULT_DRIVER_CAPACITY_KG),
            'motivo': 'Repartidor disponible para optimización multi-ruta.',
        }

    def _ordered_driver_candidates(self, drivers, remaining_orders, used_driver_ids, preferred_driver_id=None):
        available = [driver for driver in drivers if driver['repartidor_id'] not in used_driver_ids]
        if not available:
            return []

        centroid = self._orders_centroid(remaining_orders)

        available.sort(
            key=lambda driver: haversine_km(
                driver['start'].lat,
                driver['start'].lng,
                centroid.lat,
                centroid.lng,
            )
        )

        if preferred_driver_id:
            preferred_index = next(
                (index for index, driver in enumerate(available) if driver['repartidor_id'] == preferred_driver_id),
                None,
            )
            if preferred_index is not None:
                preferred_driver = available.pop(preferred_index)
                available.insert(0, preferred_driver)

        return available

    def _build_route_for_driver(self, driver, remaining_orders, capacity_limit, rules):
        route_capacity = float(min(capacity_limit, driver['capacity']))
        max_duration_mins = float(rules.get('max_duration_mins') or DURATION_WARNING_MINUTES)
        max_area_km2 = float(rules.get('max_area_km2') or MAX_ROUTE_AREA_KM2)
        max_distance_km = float(rules.get('max_distance_km') or DISTANCE_WARNING_KM)

        within_radius, _ = cluster_by_radius(
            remaining_orders,
            lambda p: (float(p.cliente.latitud), float(p.cliente.longitud)),
            driver['start'].lat,
            driver['start'].lng,
            MAX_ROUTE_RADIUS_KM,
        )
        if not within_radius:
            return None

        scored = self._score_orders(within_radius, driver['start'], route_capacity, rules)
        ordered_candidates = [item['pedido'] for item in scored]
        selected = self._select_route_orders(
            driver['start'],
            ordered_candidates,
            route_capacity,
            max_duration_mins,
            max_area_km2,
            max_distance_km,
        )
        if not selected:
            return None

        ordered_stops, total_distance = self._nearest_neighbor(driver['start'], selected)
        duration_mins = self._estimate_duration(total_distance, len(ordered_stops))
        selected_ids = {stop['pedido'].id for stop in ordered_stops}
        warehouse = self._select_warehouse_for_orders([stop['pedido'] for stop in ordered_stops])

        route = {
            'repartidor_id': driver['repartidor_id'],
            'repartidor_nombre': driver.get('name'),
            'repartidor_motivo': driver.get('motivo'),
            'aliado_id': warehouse.id if warehouse else None,
            'aliado_nombre': warehouse.user.nombre if warehouse else None,
            'start': {'lat': driver['start'].lat, 'lng': driver['start'].lng},
            'pedidos_seleccionados': [stop['pedido'] for stop in ordered_stops],
            'orden_entrega': ordered_stops,
            'distancia_total_km': round(total_distance, 2),
            'duracion_total_mins': duration_mins,
            'capacidad_usada_kg': round(
                sum(float(stop['pedido'].peso_total_kg or 0) for stop in ordered_stops),
                2,
            ),
            'geometria': {
                'type': 'LineString',
                'coordinates': [[driver['start'].lng, driver['start'].lat]] + [
                    [stop['lng'], stop['lat']] for stop in ordered_stops
                ],
            },
            'radio_permitido_km': MAX_ROUTE_RADIUS_KM,
            'radio_permitido_m2': max_area_km2,
            'dentro_radio_permitido': True,
            'max_duration_mins': max_duration_mins,
            'max_distance_km': max_distance_km,
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
            'pedidos_descartados_por_scoring': self._discarded_from_scoring(scored, selected_ids),
        }
        return route

    def _select_route_orders(self, start, candidatos, capacity_limit, max_duration_mins, max_area_km2, max_distance_km):
        remaining = list(candidatos)
        selected = []
        used_capacity = 0.0

        while remaining:
            current = start if not selected else GeoPoint(
                float(selected[-1].cliente.latitud),
                float(selected[-1].cliente.longitud),
            )
            next_order = min(
                remaining,
                key=lambda pedido: haversine_km(
                    current.lat,
                    current.lng,
                    float(pedido.cliente.latitud),
                    float(pedido.cliente.longitud),
                ),
            )

            weight = float(next_order.peso_total_kg or 0)
            if used_capacity + weight > capacity_limit:
                if not selected:
                    remaining.remove(next_order)
                    continue
                break

            projected_selected = selected + [next_order]
            ordered_stops, projected_distance = self._nearest_neighbor(start, projected_selected)
            projected_duration = self._estimate_duration(projected_distance, len(projected_selected))
            projected_area = self._estimate_route_area_km2(start, projected_selected)

            if (
                projected_duration > max_duration_mins
                or projected_distance > max_distance_km
                or projected_area > max_area_km2
            ):
                if not selected:
                    remaining.remove(next_order)
                    continue
                break

            selected.append(next_order)
            used_capacity += weight
            remaining.remove(next_order)

        return selected

    def _estimate_route_area_km2(self, start, pedidos):
        points = [(start.lat, start.lng)] + [
            (float(pedido.cliente.latitud), float(pedido.cliente.longitud))
            for pedido in pedidos
        ]
        _, _, radius_km = get_route_bounding_circle(points)
        return round(math.pi * (radius_km ** 2), 2)

    def _select_warehouse_for_orders(self, pedidos):
        warehouses = list(
            Aliado.objects.select_related('user').filter(latitud__isnull=False, longitud__isnull=False)
        )
        if not warehouses or not pedidos:
            return None

        centroid = self._orders_centroid(pedidos)
        return min(
            warehouses,
            key=lambda warehouse: haversine_km(
                centroid.lat,
                centroid.lng,
                float(warehouse.latitud),
                float(warehouse.longitud),
            ),
        )

    def _build_unassigned_reason(self, pedido, drivers, rules, capacity_limit):
        if not drivers:
            return {
                'pedido_id': pedido.id,
                'motivo': 'No hay repartidores disponibles con coordenadas.',
            }

        distances = [
            haversine_km(
                driver['start'].lat,
                driver['start'].lng,
                float(pedido.cliente.latitud),
                float(pedido.cliente.longitud),
            )
            for driver in drivers
        ]
        nearest_distance = min(distances) if distances else None
        weight = float(pedido.peso_total_kg or 0)
        max_duration_mins = float(rules.get('max_duration_mins') or DURATION_WARNING_MINUTES)
        estimated_single_duration = self._estimate_duration(nearest_distance or 0, 1)

        if nearest_distance is not None and nearest_distance > MAX_ROUTE_RADIUS_KM:
            motivo = 'No hay repartidores disponibles dentro del radio permitido.'
        elif weight > capacity_limit:
            motivo = 'El peso del pedido supera la capacidad disponible.'
        elif estimated_single_duration > max_duration_mins:
            motivo = 'El pedido excede el tiempo máximo permitido para una ruta urbana.'
        else:
            motivo = 'No fue posible combinar el pedido con otra ruta sin violar las reglas configuradas.'

        return {
            'pedido_id': pedido.id,
            'motivo': motivo,
            'distancia_km': round(nearest_distance, 2) if nearest_distance is not None else None,
        }

    def _format_unassigned_order(self, pedido, repartidor=None, motivo="No fue posible asignar el pedido."):
        cliente = getattr(pedido, "cliente", None)

        return {
            "pedido_id": getattr(pedido, "id", None),
            "cliente": getattr(cliente, "nombre", None) or getattr(cliente, "name", None) or "Cliente sin nombre",
            "direccion": getattr(cliente, "direccion", None) or getattr(cliente, "address", None) or "",
            "latitud": float(cliente.latitud) if cliente and cliente.latitud is not None else None,
            "longitud": float(cliente.longitud) if cliente and cliente.longitud is not None else None,
            "repartidor_id": getattr(repartidor, "id", None) if repartidor else None,
            "motivo": motivo,
        }

    def _build_multi_route_explanation(self, routes, unassigned_orders, summary):
        if not routes:
            return 'No se pudieron crear rutas viables para los pedidos pendientes.'

        route_fragments = []
        for route in routes:
            route_fragments.append(
                f"repartidor {route.get('repartidor_nombre') or route.get('repartidor_id')} con {len(route.get('pedidos_seleccionados', []))} pedidos"
            )

        unassigned_count = len(unassigned_orders)
        return (
            f"Se crearon {summary['rutas_creadas']} rutas para cubrir {summary['pedidos_asignados']} pedidos. "
            f"Rutas generadas: {', '.join(route_fragments)}. "
            f"Pedidos no asignados: {unassigned_count}. "
            f"No se repiten pedidos entre rutas y cada repartidor se usa una sola vez mientras haya alternativas disponibles."
        )


def haversine_km(lat1, lon1, lat2, lon2):
    """Wrapper que delega a la función de geospatial_helpers."""
    from logistics.services.geospatial_helpers import haversine_km as calculate_haversine
    return calculate_haversine(lat1, lon1, lat2, lon2)


def to_decimal(value):
    return Decimal(str(round(float(value), 8)))
