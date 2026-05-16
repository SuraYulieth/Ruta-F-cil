class RouteMetricsService:
    """
    Metrics for ABP evidence. Values are intentionally transparent estimates:
    they compare the system route against a manual Excel-style planning baseline.
    """

    manual_minutes_per_order = 8
    manual_extra_distance_factor = 1.35

    def build(self, optimizer_result):
        selected_count = len(optimizer_result.get('pedidos_seleccionados', []))
        distance = float(optimizer_result.get('distancia_total_km') or 0)
        duration = int(optimizer_result.get('duracion_total_mins') or 0)
        manual_planning_minutes = selected_count * self.manual_minutes_per_order
        manual_distance = round(distance * self.manual_extra_distance_factor, 2)
        saved_distance = round(max(0, manual_distance - distance), 2)

        return {
            'complejidad': {
                'mejor_caso': 'O(n)',
                'caso_promedio': 'O(n^2)',
                'peor_caso': 'O(n^2)',
                'detalle': 'Scoring lineal sobre pedidos y ordenamiento nearest-neighbor con busqueda repetida.',
            },
            'comparacion_manual_excel': {
                'metodo_manual': 'Asignacion visual/manual en Excel sin calculo geografico entre puntos.',
                'tiempo_planeacion_manual_estimado_mins': manual_planning_minutes,
                'distancia_manual_estimada_km': manual_distance,
                'distancia_sistema_km': distance,
                'ahorro_distancia_estimado_km': saved_distance,
                'tiempo_sistema_estimado_mins': duration,
            },
            'evidencia_abp': {
                'pedidos_asignados': [pedido.id for pedido in optimizer_result.get('pedidos_seleccionados', [])],
                'bodega_seleccionada': optimizer_result.get('aliado_nombre'),
                'repartidor_seleccionado': optimizer_result.get('repartidor_nombre'),
                'distancia_total_km': distance,
                'tiempo_estimado_mins': duration,
                'capacidad_usada_kg': optimizer_result.get('capacidad_usada_kg'),
                'explicacion_ia': optimizer_result.get('explicacion'),
            },
        }
