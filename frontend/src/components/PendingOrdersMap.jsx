import { GoogleMap, InfoWindowF, MarkerF, PolylineF, useJsApiLoader } from '@react-google-maps/api';
import { useMemo, useState } from 'react';

const GOOGLE_MAPS_LIBRARIES = ['places'];
const DEFAULT_DRIVER_LOCATION = { lat: 4.711, lng: -74.0721 };
const MAP_CONTAINER_STYLE = { width: '100%', height: '480px' };
const ROUTE_COLORS = ['#2563eb', '#16a34a', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6'];
const UNASSIGNED_COLOR = '#dc2626';
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

export const PendingOrdersMap = ({
  orders,
  selectedOrderIds = [],
  routeGeometry,
  routeStops = [],
  warehouses = [],
  selectedWarehouseId,
  driverLocation = DEFAULT_DRIVER_LOCATION,
  optimization = null,
}) => {
  const [activeOrder, setActiveOrder] = useState(null);
  const apiKey = getGoogleMapsApiKey();

  const { isLoaded, loadError } = useJsApiLoader({
    id: 'ruta-facil-google-maps',
    googleMapsApiKey: apiKey || '',
    libraries: GOOGLE_MAPS_LIBRARIES,
  });

  const driverPosition = {
    lat: toNumber(driverLocation?.lat) ?? DEFAULT_DRIVER_LOCATION.lat,
    lng: toNumber(driverLocation?.lng) ?? DEFAULT_DRIVER_LOCATION.lng,
  };

  const pendingOrders = useMemo(() => (
    orders
      .filter((order) => String(order.estado || order.status || '').toLowerCase() === 'pendiente')
      .map((order) => ({ ...order, position: getOrderPosition(order) }))
      .filter((order) => order.position)
  ), [orders]);
  const warehouseMarkers = useMemo(() => (
    warehouses
      .map((warehouse) => ({ ...warehouse, position: getWarehousePosition(warehouse) }))
      .filter((warehouse) => warehouse.position)
  ), [warehouses]);

  const optimizer = optimization?.optimizer;
  const routes = useMemo(() => {
    if (optimizer?.routes?.length) {
      return optimizer.routes;
    }
    if (routeGeometry?.coordinates?.length || routeStops.length) {
      return [{
        repartidor_id: optimization?.route?.repartidor?.id || optimization?.route?.repartidor_id,
        repartidor_nombre: optimization?.route?.repartidor?.nombre || optimization?.route?.repartidor_nombre,
        aliado_id: optimization?.route?.aliado?.id || optimization?.route?.aliado_id,
        aliado_nombre: optimization?.route?.aliado?.user?.nombre || optimization?.route?.aliado_nombre,
        pedidos_seleccionados: selectedOrderIds,
        orden_entrega: routeStops.map((stop, index) => ({
          pedido_id: stop.pedido?.id ?? stop.pedido_id,
          orden: stop.orden ?? index + 1,
          lat: stop.latitud ?? stop.lat,
          lng: stop.longitud ?? stop.lng,
          distancia_desde_anterior_km: stop.distancia_desde_anterior_km,
          tiempo_estimado_desde_anterior_mins: stop.tiempo_estimado_desde_anterior_mins,
        })),
        geometria: routeGeometry,
      }];
    }
    return [];
  }, [optimizer, routeGeometry, routeStops, optimization?.route, selectedOrderIds]);
  const unassignedOrders = optimizer?.unassigned_orders || optimizer?.pedidos_descartados || [];
  const routePaths = useMemo(() => routes.map((route) => getRoutePath(route.geometria || route.routeGeometry)), [routes]);
  const selectedSet = useMemo(() => new Set(selectedOrderIds.map(Number)), [selectedOrderIds]);
  const selectedOrdersByRoute = useMemo(() => {
    const mapping = new Map();
    routes.forEach((route, routeIndex) => {
      (route.pedidos_seleccionados || []).forEach((pedidoId) => {
        mapping.set(Number(pedidoId), routeIndex);
      });
    });
    return mapping;
  }, [routes]);
  const unassignedSet = useMemo(() => new Set(unassignedOrders.map((item) => Number(item.pedido_id))), [unassignedOrders]);
  const stopOrderByPedidoId = useMemo(() => {
    if (routes.length) {
      const entries = routes.flatMap((route, routeIndex) => (route.orden_entrega || []).map((stop) => [
        Number(stop.pedido?.id ?? stop.pedido_id),
        { orden: stop.orden, routeIndex },
      ]));
      return new Map(entries.filter(([pedidoId]) => Number.isFinite(pedidoId)));
    }
    return getStopOrderByPedidoId(routeStops);
  }, [routes, routeStops]);

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
            options={MAP_OPTIONS}
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
              const stopOrderEntry = stopOrderByPedidoId.get(Number(order.id));
              const routeIndex = selectedOrdersByRoute.get(Number(order.id));
              const isUnassigned = unassignedSet.has(Number(order.id));
              const labelText = stopOrderEntry?.orden ? String(stopOrderEntry.orden) : String(order.id);
              const routeColor = routeIndex !== undefined ? ROUTE_COLORS[routeIndex % ROUTE_COLORS.length] : null;

              return (
                <MarkerF
                  key={order.id}
                  position={order.position}
                  label={{
                    text: labelText,
                    color: isUnassigned ? UNASSIGNED_COLOR : routeColor || (selectedSet.has(Number(order.id)) ? '#0f172a' : '#ffffff'),
                    fontWeight: '800',
                  }}
                  title={`${order.customer} - ${order.destination}${isUnassigned ? ' (no asignado)' : ''}`}
                  onClick={() => setActiveOrder(order)}
                />
              );
            })}

            {routePaths.map((path, index) => (
              path.length > 1 ? (
                <PolylineF
                  key={`route-path-${index}`}
                  path={path}
                  options={{
                    strokeColor: ROUTE_COLORS[index % ROUTE_COLORS.length],
                    strokeOpacity: 0.9,
                    strokeWeight: 5,
                  }}
                />
              ) : null
            ))}

            {activeOrder && (
              <InfoWindowF
                position={activeOrder.position}
                onCloseClick={() => setActiveOrder(null)}
              >
                <div className="map-info-window">
                  <strong>{activeOrder.customer}</strong>
                  <p>{activeOrder.destination}</p>
                  <span>Pedido #{activeOrder.id}</span>
                  {selectedOrdersByRoute.has(Number(activeOrder.id)) && (
                    <p>Ruta #{selectedOrdersByRoute.get(Number(activeOrder.id)) + 1}</p>
                  )}
                  {unassignedSet.has(Number(activeOrder.id)) && (
                    <p className="warning-text">
                      {unassignedOrders.find((item) => Number(item.pedido_id) === Number(activeOrder.id))?.motivo || 'Pedido no asignado'}
                    </p>
                  )}
                </div>
              </InfoWindowF>
            )}
          </GoogleMap>
        )}
      </div>
    </section>
  );
};
