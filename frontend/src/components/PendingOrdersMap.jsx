const DEFAULT_CENTER = { lat: 4.711, lng: -74.0721 };

const getPointStyle = (order) => {
  const lat = Number(order.latitude || DEFAULT_CENTER.lat);
  const lng = Number(order.longitude || DEFAULT_CENTER.lng);
  const x = Math.min(92, Math.max(8, 50 + (lng - DEFAULT_CENTER.lng) * 900));
  const y = Math.min(92, Math.max(8, 50 - (lat - DEFAULT_CENTER.lat) * 900));
  return { left: `${x}%`, top: `${y}%` };
};

export const PendingOrdersMap = ({ orders, selectedOrderIds = [], routeGeometry }) => {
  const pendingOrders = orders.filter((order) => order.status === 'Pendiente' || order.estado === 'Pendiente');
  const selectedSet = new Set(selectedOrderIds);
  const pathPoints = routeGeometry?.coordinates?.map(([lng, lat]) => {
    const x = Math.min(92, Math.max(8, 50 + (Number(lng) - DEFAULT_CENTER.lng) * 900));
    const y = Math.min(92, Math.max(8, 50 - (Number(lat) - DEFAULT_CENTER.lat) * 900));
    return `${x},${y}`;
  }).join(' ');

  return (
    <section className="panel map-panel">
      <div className="panel-title-row">
        <h2>Pedidos pendientes</h2>
        <span className="count">{pendingOrders.length}</span>
      </div>

      <div className="mock-map" aria-label="Mapa de pedidos pendientes">
        <div className="map-grid" />
        {pathPoints && (
          <svg className="route-line" viewBox="0 0 100 100" preserveAspectRatio="none">
            <polyline points={pathPoints} />
          </svg>
        )}

        {pendingOrders.map((order) => (
          <div
            key={order.id}
            className={`map-marker ${selectedSet.has(order.id) ? 'selected' : ''}`}
            style={getPointStyle(order)}
            title={`${order.customer} - ${order.destination}`}
          >
            {order.id}
          </div>
        ))}
      </div>
    </section>
  );
};
