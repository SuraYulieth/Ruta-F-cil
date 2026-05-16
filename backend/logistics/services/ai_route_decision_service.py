class AiRouteDecisionService:
    """
    Rule-based explanation layer. It can later delegate to an LLM while keeping
    this stable interface for the optimizer and API.
    """

    def explain(self, optimizer_result):
        selected = optimizer_result.get('pedidos_seleccionados', [])
        discarded = optimizer_result.get('pedidos_descartados', [])
        distance = optimizer_result.get('distancia_total_km', 0)
        duration = optimizer_result.get('duracion_total_mins', 0)
        capacity_used = optimizer_result.get('capacidad_usada_kg', 0)

        alerts = []
        recommendations = []

        if not selected:
            alerts.append('No hay pedidos viables para agrupar en este momento.')
            recommendations.append('Verificar coordenadas de clientes y disponibilidad de pedidos pendientes.')

        if duration > 90:
            alerts.append('La ruta estimada supera 90 minutos.')
            recommendations.append('Reducir el número de paradas o dividir el recorrido en dos rutas.')

        if distance > 25:
            alerts.append('La distancia total es alta para una ruta urbana.')
            recommendations.append('Validar con una API de tráfico antes de asignar definitivamente.')

        if selected and capacity_used == 0:
            recommendations.append('Registrar peso o volumen para mejorar la selección por capacidad.')

        discarded_summary = [
            {
                'pedido_id': item.get('pedido_id'),
                'motivo': item.get('motivo'),
                'score': item.get('score'),
            }
            for item in discarded
        ]

        return {
            'explicacion': optimizer_result.get('explicacion', ''),
            'alertas': alerts,
            'recomendaciones': recommendations,
            'pedidos_descartados': discarded_summary,
            'sugerencia_mejora': self._suggest_next_step(selected, discarded),
        }

    def _suggest_next_step(self, selected, discarded):
        if discarded:
            return 'Completar coordenadas, peso y ventanas de entrega para aumentar la precisión del algoritmo.'
        if len(selected) <= 1:
            return 'Esperar más pedidos cercanos antes de consolidar si la entrega no es urgente.'
        return 'Asignar la ruta y monitorear tiempos reales para calibrar velocidad promedio y scoring.'
