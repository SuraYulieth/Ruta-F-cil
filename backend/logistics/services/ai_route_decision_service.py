from logistics.config import MAX_ROUTE_RADIUS_KM, MAX_ROUTE_AREA_KM2, DURATION_WARNING_MINUTES, DISTANCE_WARNING_KM


class AiRouteDecisionService:
    """
    Capa IA explicativa basada en reglas auditables.

    Convierte la salida del optimizador en razones, alertas y recomendaciones
    sin usar un modelo opaco.
    """

    def explain(self, optimizer_result):
        routes = optimizer_result.get('routes') or optimizer_result.get('rutas', [])
        primary_route = optimizer_result.get('route') or optimizer_result.get('ruta_principal')
        selected = optimizer_result.get('pedidos_seleccionados', [])
        discarded = optimizer_result.get('unassigned_orders') or optimizer_result.get('pedidos_descartados', [])
        distance = float(optimizer_result.get('distancia_total_km') or 0)
        duration = int(optimizer_result.get('duracion_total_mins') or 0)
        capacity_used = float(optimizer_result.get('capacidad_total_usada_kg') or 0)
        metrics = optimizer_result.get('metricas', {})
        summary = optimizer_result.get('summary', {})
        driver_diagnostics = optimizer_result.get('driver_diagnostics', {}) or {}
        allowed_radius = float(optimizer_result.get('radio_permitido_km') or MAX_ROUTE_RADIUS_KM)
        total_routes = int(optimizer_result.get('total_rutas') or summary.get('rutas_creadas') or len(routes) or 0)
        outside_radius_drivers = int(driver_diagnostics.get('fuera_de_radio') or 0)

        alerts = []
        recommendations = []

        if not selected:
            if driver_diagnostics.get('total_repartidores', 0) > 0 and driver_diagnostics.get('aptos_para_optimizar', 0) == 0:
                alerts.append(self._driver_diagnostics_explanation(driver_diagnostics))
                recommendations.append('Activar un repartidor, verificar coordenadas y confirmar que no tenga ruta activa.')
            else:
                alerts.append('No hay pedidos viables para agrupar en este momento.')
                recommendations.append('Verificar que los pedidos pendientes tengan coordenadas válidas y capacidad suficiente.')
        else:
            outside_radius_count = sum(
                1 for item in discarded if 'radio' in str(item.get('motivo', '')).lower()
            )
            if outside_radius_count > 0:
                alerts.append(
                    f'Se encontraron {outside_radius_count} pedidos fuera del radio máximo permitido '
                    f'({allowed_radius:.2f} km / {MAX_ROUTE_AREA_KM2} km²).'
                )
                recommendations.append(
                    f'Crear rutas adicionales o reasignar esos {outside_radius_count} pedidos a repartidores más cercanos.'
                )

            if summary.get('pedidos_no_asignados', 0) > 0:
                recommendations.append(
                    f'{summary["pedidos_no_asignados"]} pedidos quedaron no asignados con motivo de cobertura/capacidad/reglas.'
                )

        if total_routes > 1:
            alerts.append(f'Se crearon {total_routes} rutas para cubrir pedidos remanentes sin repetir pedidos.')
            recommendations.append('Revisar cada ruta por separado y validar ventanas de entrega reales por repartidor.')

        if outside_radius_drivers > 0:
            alerts.append(
                f'{outside_radius_drivers} repartidor(es) están fuera del radio permitido '
                f'({allowed_radius:.2f} km).'
            )
            recommendations.append(
                'Revisar detalle de repartidores fuera de radio para moverlos al centro de demanda sugerido.'
            )

        if duration > DURATION_WARNING_MINUTES:
            alerts.append(f'La optimización acumulada supera {DURATION_WARNING_MINUTES} minutos ({duration} min).')
            recommendations.append('Dividir rutas largas y mover paradas lejanas a otras rutas/repartidores.')

        if distance > DISTANCE_WARNING_KM:
            alerts.append(f'La distancia total es alta para reparto urbano ({distance:.2f} km).')
            recommendations.append('Validar tránsito real y consolidar paradas cercanas para reducir kilómetros.')

        if selected and capacity_used == 0:
            recommendations.append('Registrar peso y volumen para mejorar decisiones por capacidad.')

        if primary_route and not primary_route.get('aliado_id'):
            alerts.append('No se pudo asociar una bodega cercana con coordenadas.')
            recommendations.append('Registrar coordenadas de bodegas/aliados para mejorar asignación geográfica.')

        if primary_route and not primary_route.get('repartidor_id'):
            alerts.append('No se encontró repartidor principal con coordenadas.')
            recommendations.append('Actualizar ubicación y estado de repartidores antes de optimizar.')

        if discarded:
            reason_samples = sorted({item.get('motivo') for item in discarded if item.get('motivo')})
            if reason_samples:
                recommendations.append('Motivos de no asignación detectados: ' + ' | '.join(reason_samples[:3]))

        discarded_summary = []
        for item in discarded:
            row = {
                'pedido_id': item.get('pedido_id'),
                'motivo': item.get('motivo'),
            }
            if 'score' in item:
                row['score'] = item.get('score')
            if 'distancia_km' in item:
                row['distancia_km'] = item.get('distancia_km')
            discarded_summary.append(row)

        confidence = self._calculate_confidence(metrics)

        return {
            'explicacion': optimizer_result.get('explicacion', ''),
            'alertas': alerts,
            'recomendaciones': recommendations,
            'pedidos_descartados': discarded_summary,
            'eficiencia': self._efficiency_summary(distance, duration, selected, primary_route, total_routes),
            'confianza': confidence,
            'radio_permitido': {
                'km': round(allowed_radius, 2),
                'm2': MAX_ROUTE_AREA_KM2,
            },
            'rutas_creadas': total_routes,
            'metricas_resumen': {
                'pedidos_candidatos': metrics.get('total_pedidos_candidatos', summary.get('total_pedidos', 0)),
                'pedidos_factibles': metrics.get('pedidos_factibles', summary.get('pedidos_asignados', 0)),
                'dentro_radio': metrics.get('pedidos_dentro_radio', 0),
                'fuera_radio': metrics.get('pedidos_fuera_radio', 0),
                'seleccionados': metrics.get('pedidos_seleccionados', summary.get('pedidos_asignados', 0)),
                'descartados': metrics.get('pedidos_descartados', summary.get('pedidos_no_asignados', 0)),
                'rutas_creadas': total_routes,
            },
            'bodega': {
                'id': primary_route.get('aliado_id') if primary_route else None,
                'nombre': primary_route.get('aliado_nombre') if primary_route else None,
            },
            'repartidor_principal': {
                'id': primary_route.get('repartidor_id') if primary_route else None,
                'nombre': primary_route.get('repartidor_nombre') if primary_route else None,
                'motivo': primary_route.get('repartidor_motivo') if primary_route else None,
            },
            'driver_diagnostics': driver_diagnostics,
            'sugerencia_mejora': self._suggest_next_step(selected, discarded, metrics, total_routes),
        }

    def _driver_diagnostics_explanation(self, diagnostics):
        parts = []
        labels = [
            ('deshabilitados', 'deshabilitados'),
            ('en_entrega', 'en entrega'),
            ('sin_coordenadas', 'sin coordenadas'),
            ('fuera_de_radio', 'fuera del radio permitido'),
            ('estado_invalido', 'con estado no disponible'),
            ('role_invalido', 'con rol no valido'),
        ]
        for key, label in labels:
            count = int(diagnostics.get(key) or 0)
            if count:
                parts.append(f'{count} {label}')

        suffix = ', '.join(parts) if parts else 'sin condiciones operativas validas'
        return (
            'No se crearon rutas porque no hay repartidores aptos para optimizar: '
            f'{suffix}.'
        )

    def _calculate_confidence(self, metrics):
        selected = int(metrics.get('pedidos_seleccionados', 0))
        total_candidates = int(metrics.get('total_pedidos_candidatos', 0) or 1)
        if selected == 0:
            return {'nivel': 'bajo', 'descripcion': 'Sin pedidos seleccionados.'}

        ratio = selected / total_candidates
        if ratio >= 0.8:
            return {
                'nivel': 'alto',
                'descripcion': 'La mayoría de pedidos pudo asignarse respetando restricciones.',
                'score': round(ratio * 100, 1),
            }
        if ratio >= 0.5:
            return {
                'nivel': 'medio',
                'descripcion': 'Parte de los pedidos requirió partición o quedó fuera por restricciones.',
                'score': round(ratio * 100, 1),
            }
        return {
            'nivel': 'bajo',
            'descripcion': 'Pocos pedidos pudieron asignarse con las reglas actuales.',
            'score': round(ratio * 100, 1),
        }

    def _efficiency_summary(self, distance, duration, selected, primary_route, total_routes):
        if not selected:
            return 'Sin pedidos seleccionados no se puede estimar eficiencia.'

        avg_distance = round(distance / len(selected), 2)
        scoring = primary_route.get('scoring', []) if primary_route else []
        best_scores = sorted(scoring, key=lambda item: item.get('score', 0), reverse=True)[:3]
        best_ids = [item.get('pedido_id') for item in best_scores]
        routes_text = 'en 1 ruta' if total_routes == 1 else f'distribuidos en {total_routes} rutas'

        return (
            f'Optimización con {len(selected)} paradas {routes_text}, '
            f'promedio de {avg_distance} km por entrega y duración total estimada de {duration} minutos. '
            f'Mejores scores: {best_ids}.'
        )

    def _suggest_next_step(self, selected, discarded, metrics, total_routes):
        if not selected:
            return 'Esperar más pedidos pendientes con coordenadas válidas.'

        outside_radius = sum(1 for item in discarded if 'radio' in str(item.get('motivo', '')).lower())
        if outside_radius > 0:
            return (
                f'Se detectaron {outside_radius} pedidos fuera del radio permitido. '
                'Crear rutas adicionales con repartidores cercanos o mantenerlos como no asignados con motivo.'
            )

        if total_routes > 1:
            return 'Asignar las rutas generadas y monitorear en operación real si alguna supera 90 minutos.'

        if len(selected) <= 1:
            return 'Esperar más pedidos cercanos para consolidar una ruta más eficiente.'

        return 'Asignar la ruta y monitorear tiempos reales para calibrar velocidad y scoring.'
