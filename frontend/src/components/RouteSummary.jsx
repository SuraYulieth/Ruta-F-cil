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

  return (
    <div className="route-summary">
      <div className="metric-grid">
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
