import { GoogleMap, InfoWindowF, MarkerF, PolylineF, useJsApiLoader } from '@react-google-maps/api';
import { useMemo, useState } from 'react';

const DEFAULT_DRIVER_LOCATION = { lat: 4.711, lng: -74.0721 };
const MAP_CONTAINER_STYLE = { width: '100%', height: '480px' };
const MAP_OPTIONS = {
  disableDefaultUI: false,
  fullscreenControl: true,
  mapTypeControl: false,
  streetViewControl: false,
};

const toNumber = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const getOrderPosition = (order) => {
  const lat = toNumber(order.latitude ?? order.latitud ?? order.cliente?.latitud);
  const lng = toNumber(order.longitude ?? order.longitud ?? order.cliente?.longitud);
  if (lat === null || lng === null) return null;
  return { lat, lng };
};

const getWarehousePosition = (warehouse) => {
  const lat = toNumber(warehouse.latitude ?? warehouse.latitud);
  const lng = toNumber(warehouse.longitude ?? warehouse.longitud);
  if (lat === null || lng === null) return null;
  return { lat, lng };
};

const getStopOrderByPedidoId = (routeStops = []) => {
  const entries = routeStops
    .map((stop) => [Number(stop.pedido?.id ?? stop.pedido_id), stop.orden])
    .filter(([pedidoId]) => Number.isFinite(pedidoId));

  return new Map(entries);
};

const getRoutePath = (routeGeometry) => {
  if (!routeGeometry?.coordinates?.length) return [];
  return routeGeometry.coordinates
    .map(([lng, lat]) => ({ lat: Number(lat), lng: Number(lng) }))
    .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lng));
};

const getGoogleMapsApiKey = () => (
  import.meta.env.VITE_GOOGLE_MAPS_API_KEY
  || import.meta.env.VITE_GOOGLE_MAPS_KEY
  || import.meta.env.VITE_GOOGLE_API_KEY
  || ''
).trim().replace(/^["']|["']$/g, '');

const getGoogleMapsMapId = () => (
  import.meta.env.VITE_GOOGLE_MAPS_MAP_ID
  || import.meta.env.VITE_GOOGLE_MAPS_ID
  || ''
).trim().replace(/^["']|["']$/g, '');

export const PendingOrdersMap = ({
  orders,
  selectedOrderIds = [],
  routeGeometry,
  routeStops = [],
  warehouses = [],
  selectedWarehouseId,
  driverLocation = DEFAULT_DRIVER_LOCATION,
}) => {
  const [activeOrder, setActiveOrder] = useState(null);
  const apiKey = getGoogleMapsApiKey();
  const mapId = getGoogleMapsMapId();

  const { isLoaded, loadError } = useJsApiLoader({
    id: 'ruta-facil-google-maps',
    googleMapsApiKey: apiKey || '',
  });

  const driverPosition = {
    lat: toNumber(driverLocation?.lat) ?? DEFAULT_DRIVER_LOCATION.lat,
    lng: toNumber(driverLocation?.lng) ?? DEFAULT_DRIVER_LOCATION.lng,
  };

  const pendingOrders = useMemo(() => (
    orders
      .filter((order) => order.status === 'Pendiente' || order.estado === 'Pendiente')
      .map((order) => ({ ...order, position: getOrderPosition(order) }))
      .filter((order) => order.position)
  ), [orders]);
  const warehouseMarkers = useMemo(() => (
    warehouses
      .map((warehouse) => ({ ...warehouse, position: getWarehousePosition(warehouse) }))
      .filter((warehouse) => warehouse.position)
  ), [warehouses]);

  const selectedSet = useMemo(() => new Set(selectedOrderIds.map(Number)), [selectedOrderIds]);
  const stopOrderByPedidoId = useMemo(() => getStopOrderByPedidoId(routeStops), [routeStops]);
  const routePath = useMemo(() => getRoutePath(routeGeometry), [routeGeometry]);

  if (!apiKey) {
    return (
      <section className="panel map-panel">
        <h2>Mapa de ruta</h2>
        <div className="error-message">
          Falta configurar VITE_GOOGLE_MAPS_API_KEY en el archivo .env del frontend.
        </div>
      </section>
    );
  }

  if (loadError) {
    return (
      <section className="panel map-panel">
        <h2>Mapa de ruta</h2>
        <div className="error-message">
          Google Maps no pudo cargarse. Verifica la API key, facturacion y permisos de dominio.
        </div>
      </section>
    );
  }

  return (
    <section className="panel map-panel">
      <div className="panel-title-row">
        <h2>Mapa de ruta</h2>
        <span className="count">{pendingOrders.length}</span>
      </div>

      {!pendingOrders.length && (
        <div className="warning-message">No hay pedidos pendientes con coordenadas para mostrar.</div>
      )}

      <div className="google-map-shell">
        {!isLoaded ? (
          <div className="empty-state">Cargando Google Maps...</div>
        ) : (
          <GoogleMap
            mapContainerStyle={MAP_CONTAINER_STYLE}
            center={driverPosition}
            zoom={14}
            options={{
              ...MAP_OPTIONS,
              mapId: mapId || undefined,
            }}
          >
            <MarkerF
              position={driverPosition}
              label={{ text: 'R', color: '#ffffff', fontWeight: '700' }}
              title="Ubicacion inicial del repartidor"
            />

            {warehouseMarkers.map((warehouse) => (
              <MarkerF
                key={`warehouse-${warehouse.id}`}
                position={warehouse.position}
                label={{
                  text: selectedWarehouseId && Number(selectedWarehouseId) === Number(warehouse.id) ? 'B*' : 'B',
                  color: '#ffffff',
                  fontWeight: '800',
                }}
                title={`Bodega: ${warehouse.name || warehouse.direccion}`}
                onClick={() => setActiveOrder({
                  id: `bodega-${warehouse.id}`,
                  customer: warehouse.name || 'Bodega',
                  destination: warehouse.direccion,
                  position: warehouse.position,
                })}
              />
            ))}

            {pendingOrders.map((order) => {
              const stopOrder = stopOrderByPedidoId.get(Number(order.id));
              const labelText = stopOrder ? String(stopOrder) : String(order.id);

              return (
                <MarkerF
                  key={order.id}
                  position={order.position}
                  label={{
                    text: labelText,
                    color: selectedSet.has(Number(order.id)) ? '#0f172a' : '#ffffff',
                    fontWeight: '800',
                  }}
                  title={`${order.customer} - ${order.destination}`}
                  onClick={() => setActiveOrder(order)}
                />
              );
            })}

            {routePath.length > 1 && (
              <PolylineF
                path={routePath}
                options={{
                  strokeColor: '#2563eb',
                  strokeOpacity: 0.9,
                  strokeWeight: 5,
                }}
              />
            )}

            {activeOrder && (
              <InfoWindowF
                position={activeOrder.position}
                onCloseClick={() => setActiveOrder(null)}
              >
                <div className="map-info-window">
                  <strong>{activeOrder.customer}</strong>
                  <p>{activeOrder.destination}</p>
                  <span>Pedido #{activeOrder.id}</span>
                </div>
              </InfoWindowF>
            )}
          </GoogleMap>
        )}
      </div>
    </section>
  );
};
