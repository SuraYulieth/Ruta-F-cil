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
        {decision?.alertas?.map((alert) => (
          <p key={alert} className="warning-text">{alert}</p>
        ))}
        {decision?.recomendaciones?.map((recommendation) => (
          <p key={recommendation} className="hint-text">{recommendation}</p>
        ))}
      </div>
    </div>
  );
};
