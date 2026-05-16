export const RouteStopsList = ({ optimization }) => {
  const routes = optimization?.optimizer?.routes?.length
    ? optimization.optimizer.routes
    : optimization?.route
      ? [optimization.route]
      : [];
  const unassignedOrders = optimization?.optimizer?.unassigned_orders || optimization?.optimizer?.pedidos_descartados || [];

  if (!routes.length && !unassignedOrders.length) {
    return <div className="empty-state">Todavia no hay paradas optimizadas.</div>;
  }

  return (
    <div className="stops-list">
      {routes.map((route, routeIndex) => (
        <div key={`${route.repartidor_id || routeIndex}-${routeIndex}`} className="decision-box">
          <h3>
            Ruta {routeIndex + 1} - {route.repartidor_nombre || route.repartidor_id || 'Sin repartidor'}
          </h3>
          {((route.paradas || route.orden_entrega || [])).map((stop) => (
            <div key={stop.id || `${routeIndex}-${stop.orden}`} className="stop-item">
              <span className="stop-order">{stop.orden}</span>
              <div>
                <h3>{stop.pedido?.customer || stop.pedido?.cliente?.nombre || `Pedido ${stop.pedido_id}`}</h3>
                <p>{stop.pedido?.destination || stop.pedido?.cliente?.direccion || ''}</p>
                <small>{stop.distancia_desde_anterior_km} km desde la parada anterior</small>
              </div>
            </div>
          ))}
          {!(route.paradas || route.orden_entrega)?.length && <p className="text-muted">Esta ruta todavía no tiene paradas serializadas.</p>}
        </div>
      ))}

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
    </div>
  );
};
