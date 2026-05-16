export const RouteSummary = ({ optimization }) => {
  if (!optimization?.optimizer) {
    return (
      <div className="route-summary empty-state">
        Optimiza una ruta para ver distancia, tiempo y capacidad estimada.
      </div>
    );
  }

  const optimizer = optimization.optimizer;
  const decision = optimization.decision;
  const metrics = optimization.metrics;
  const summary = optimizer.summary || {};
  const routes = optimizer.routes?.length ? optimizer.routes : optimizer.route ? [optimizer.route] : [];
  const unassignedOrders = optimizer.unassigned_orders || optimizer.pedidos_descartados || [];

  return (
    <div className="route-summary">
      <div className="metric-grid">
        <div className="metric">
          <span>Total pedidos</span>
          <strong>{summary.total_pedidos ?? optimizer.pedidos_seleccionados?.length ?? 0}</strong>
        </div>
        <div className="metric">
          <span>Rutas</span>
          <strong>{summary.rutas_creadas ?? routes.length}</strong>
        </div>
        <div className="metric">
          <span>Asignados</span>
          <strong>{summary.pedidos_asignados ?? optimizer.pedidos_seleccionados?.length ?? 0}</strong>
        </div>
        <div className="metric">
          <span>No asignados</span>
          <strong>{summary.pedidos_no_asignados ?? unassignedOrders.length}</strong>
        </div>
        <div className="metric">
          <span>Distancia</span>
          <strong>{optimizer.distancia_total_km} km</strong>
        </div>
        <div className="metric">
          <span>Tiempo</span>
          <strong>{optimizer.duracion_total_mins} min</strong>
        </div>
        <div className="metric">
          <span>Capacidad</span>
          <strong>{optimizer.capacidad_usada_kg} kg</strong>
        </div>
      </div>

      <div className="decision-box">
        <h3>Decision inteligente</h3>
        <p>{decision?.explicacion}</p>
        {decision?.eficiencia && <p>{decision.eficiencia}</p>}
        {decision?.repartidor?.nombre && (
          <p className="hint-text">Repartidor sugerido: {decision.repartidor.nombre}</p>
        )}
        {decision?.bodega?.nombre && (
          <p className="hint-text">Bodega sugerida: {decision.bodega.nombre}</p>
        )}
        {decision?.alertas?.map((alert) => (
          <p key={alert} className="warning-text">{alert}</p>
        ))}
        {decision?.recomendaciones?.map((recommendation) => (
          <p key={recommendation} className="hint-text">{recommendation}</p>
        ))}
      </div>

      {routes.length > 0 && (
        <div className="decision-box">
          <h3>Rutas generadas</h3>
          {routes.map((route, index) => (
            <div key={`${route.repartidor_id || index}-${index}`} className="route-summary-card">
              <p className="hint-text">
                Ruta {index + 1} - Repartidor: {route.repartidor_nombre || route.repartidor_id || 'Sin reparto'}
              </p>
              <p>Pedidos: {(route.pedidos_seleccionados || []).join(', ')}</p>
              <p>
                Distancia: {route.distancia_total_km} km | Tiempo: {route.duracion_total_mins} min | Bodega: {route.aliado_nombre || 'Sin bodega'}
              </p>
            </div>
          ))}
        </div>
      )}

      {unassignedOrders.length > 0 && (
        <div className="decision-box">
          <h3>Pedidos no asignados</h3>
          {unassignedOrders.map((item) => (
            <p key={item.pedido_id} className="warning-text">
              Pedido #{item.pedido_id}: {item.motivo}
            </p>
          ))}
        </div>
      )}

      {metrics && (
        <div className="decision-box">
          <h3>Evidencia ABP</h3>
          <p>Complejidad: mejor {metrics.complejidad?.mejor_caso}, promedio {metrics.complejidad?.caso_promedio}, peor {metrics.complejidad?.peor_caso}.</p>
          <p>{metrics.complejidad?.detalle}</p>
          <p>
            Manual Excel: {metrics.comparacion_manual_excel?.distancia_manual_estimada_km} km estimados.
            Sistema: {metrics.comparacion_manual_excel?.distancia_sistema_km} km.
          </p>
          <p>Ahorro estimado: {metrics.comparacion_manual_excel?.ahorro_distancia_estimado_km} km.</p>
        </div>
      )}
    </div>
  );
};
