export const RouteStopsList = ({ optimization }) => {
  const stops = optimization?.route?.paradas || [];

  if (!stops.length) {
    return <div className="empty-state">Todavia no hay paradas optimizadas.</div>;
  }

  return (
    <div className="stops-list">
      {stops.map((stop) => (
        <div key={stop.id} className="stop-item">
          <span className="stop-order">{stop.orden}</span>
          <div>
            <h3>{stop.pedido.customer}</h3>
            <p>{stop.pedido.destination}</p>
            <small>{stop.distancia_desde_anterior_km} km desde la parada anterior</small>
          </div>
        </div>
      ))}
    </div>
  );
};
