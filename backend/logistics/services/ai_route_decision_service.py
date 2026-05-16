class AiRouteDecisionService:
    """
    Capa IA explicativa basada en reglas auditables.
    No predice con un modelo opaco: convierte el resultado del optimizador en
    razones, alertas y recomendaciones. La interfaz queda lista para delegar a
    un LLM o motor de decision externo mas adelante.
    """

    def explain(self, optimizer_result):
        selected = optimizer_result.get('pedidos_seleccionados', [])
        discarded = optimizer_result.get('pedidos_descartados', [])
        distance = optimizer_result.get('distancia_total_km', 0)
        duration = optimizer_result.get('duracion_total_mins', 0)
        capacity_used = optimizer_result.get('capacidad_usada_kg', 0)
        scoring = optimizer_result.get('scoring', [])

        alerts = []
        recommendations = []

        if not selected:
            alerts.append('No hay pedidos viables para agrupar en este momento.')
            recommendations.append('Verificar coordenadas de clientes y disponibilidad de pedidos pendientes.')

        if duration > 90:
            alerts.append('La ruta estimada supera 90 minutos.')
            recommendations.append('Reducir el numero de paradas o dividir el recorrido en dos rutas.')

        if distance > 25:
            alerts.append('La distancia total es alta para una ruta urbana.')
            recommendations.append('Validar con una API de trafico antes de asignar definitivamente.')

        if selected and capacity_used == 0:
            recommendations.append('Registrar peso o volumen para mejorar la seleccion por capacidad.')

        if not optimizer_result.get('aliado_id'):
            alerts.append('No se pudo asociar una bodega cercana con coordenadas.')
            recommendations.append('Registrar coordenadas de aliados/bodegas para completar la asignacion tienda-pedido.')

        if not optimizer_result.get('repartidor_id'):
            alerts.append('No se encontro repartidor disponible con coordenadas.')
            recommendations.append('Actualizar ubicacion y estado de los repartidores antes de optimizar.')

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
            'eficiencia': self._efficiency_summary(distance, duration, selected, scoring),
            'bodega': {
                'id': optimizer_result.get('aliado_id'),
                'nombre': optimizer_result.get('aliado_nombre'),
            },
            'repartidor': {
                'id': optimizer_result.get('repartidor_id'),
                'nombre': optimizer_result.get('repartidor_nombre'),
                'motivo': optimizer_result.get('repartidor_motivo'),
            },
            'sugerencia_mejora': self._suggest_next_step(selected, discarded),
        }

    def _efficiency_summary(self, distance, duration, selected, scoring):
        if not selected:
            return 'Sin pedidos seleccionados no se puede estimar eficiencia.'
        avg_distance = round(distance / len(selected), 2) if selected else 0
        best_scores = sorted(scoring, key=lambda item: item.get('score', 0), reverse=True)[:3]
        return (
            f"Ruta con {len(selected)} paradas, promedio aproximado de {avg_distance} km por entrega "
            f"y duracion total estimada de {duration} minutos. Mejores scores: "
            f"{[item.get('pedido_id') for item in best_scores]}."
        )

    def _suggest_next_step(self, selected, discarded):
        if discarded:
            return 'Completar coordenadas, peso y ventanas de entrega para aumentar la precision del algoritmo.'
        if len(selected) <= 1:
            return 'Esperar mas pedidos cercanos antes de consolidar si la entrega no es urgente.'
        return 'Asignar la ruta y monitorear tiempos reales para calibrar velocidad promedio y scoring.'
