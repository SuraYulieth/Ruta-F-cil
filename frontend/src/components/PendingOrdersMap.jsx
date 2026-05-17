import { CircleF, GoogleMap, InfoWindowF, MarkerF, PolylineF, useJsApiLoader } from '@react-google-maps/api';
import { useMemo, useState } from 'react';

const GOOGLE_MAPS_LIBRARIES = ['places'];
const DEFAULT_DRIVER_LOCATION = { lat: 4.711, lng: -74.0721 };
const MAP_CONTAINER_STYLE = { width: '100%', height: '480px' };
const ROUTE_COLORS = ['#2563eb', '#16a34a', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6'];
const UNASSIGNED_COLOR = '#dc2626';
const MAX_PENDING_MARKERS = 30;
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
  selectedDriver = null,
  isAdminMode = false,
  onDriverLocationDraftChange,
  optimization = null,
  routes: persistedRoutes = [],
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
  const visiblePendingOrders = useMemo(
    () => pendingOrders.slice(0, MAX_PENDING_MARKERS),
    [pendingOrders]
  );
  const warehouseMarkers = useMemo(() => (
    warehouses
      .map((warehouse) => ({ ...warehouse, position: getWarehousePosition(warehouse) }))
      .filter((warehouse) => warehouse.position)
  ), [warehouses]);

  const optimizer = optimization?.optimizer;
  const driverDiagnostics = optimizer?.driver_diagnostics || optimization?.decision?.driver_diagnostics || null;
  const coverageRecommendation = driverDiagnostics?.coverage_recommendation || null;
  const demandCenter = coverageRecommendation?.centro_demanda
    ? {
        lat: toNumber(coverageRecommendation.centro_demanda.latitud),
        lng: toNumber(coverageRecommendation.centro_demanda.longitud),
      }
    : null;
  const diagnosticDriverMarkers = useMemo(() => (
    (driverDiagnostics?.detalle || [])
      .map((driver) => {
        const lat = toNumber(driver.coordenadas_actuales?.latitud);
        const lng = toNumber(driver.coordenadas_actuales?.longitud);
        if (lat === null || lng === null) return null;
        return {
          ...driver,
          position: { lat, lng },
          isOutsideRadius: Number(driver.distancia_al_centro_demanda_km) > Number(driver.radio_maximo_km || 0),
        };
      })
      .filter(Boolean)
  ), [driverDiagnostics]);
  const outsideRadiusRecommendedMarkers = useMemo(() => (
    (driverDiagnostics?.detalle || [])
      .map((driver) => {
        if (
          Number(driver.distancia_al_centro_demanda_km) <= Number(driver.radio_maximo_km || 0)
          || !driver.coordenadas_recomendadas
        ) {
          return null;
        }

        const lat = toNumber(driver.coordenadas_recomendadas?.latitud);
        const lng = toNumber(driver.coordenadas_recomendadas?.longitud);
        if (lat === null || lng === null) return null;

        return {
          id: driver.id,
          nombre: driver.nombre,
          position: { lat, lng },
          zona: driver.zona_sugerida,
          message: driver.mensaje_activacion,
        };
      })
      .filter(Boolean)
  ), [driverDiagnostics]);
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
    return persistedRoutes.filter((route) => ['asignada', 'en_ruta', 'calculada'].includes(String(route.estado_ruta || '').toLowerCase()));
  }, [optimizer, routeGeometry, routeStops, optimization?.route, selectedOrderIds, persistedRoutes]);
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
  const routeStopMarkers = useMemo(() => (
    routes.flatMap((route, routeIndex) => (
      (route.paradas || route.orden_entrega || [])
        .map((stop) => {
          const pedido = stop.pedido || {};
          const lat = toNumber(stop.latitud ?? stop.lat ?? pedido.latitude ?? pedido.latitud);
          const lng = toNumber(stop.longitud ?? stop.lng ?? pedido.longitude ?? pedido.longitud);
          if (lat === null || lng === null) return null;
          return {
            id: `${route.id || routeIndex}-${stop.id || stop.orden || pedido.id}`,
            pedidoId: pedido.id ?? stop.pedido_id,
            routeId: route.id,
            routeIndex,
            orden: stop.orden,
            customer: pedido.customer || pedido.cliente_nombre || pedido.cliente?.nombre || `Pedido #${pedido.id ?? stop.pedido_id}`,
            destination: pedido.destination || pedido.direccion || pedido.cliente?.direccion || '',
            position: { lat, lng },
          };
        })
        .filter(Boolean)
    ))
  ), [routes]);

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
        <span className="count">{visiblePendingOrders.length}</span>
      </div>

      {pendingOrders.length > MAX_PENDING_MARKERS && (
        <div className="warning-message">
          Mostrando {MAX_PENDING_MARKERS} de {pendingOrders.length} pedidos pendientes para evitar saturacion del mapa.
        </div>
      )}

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
              label={{ text: 'R', color: '#0f172a', fontWeight: '700' }}
              title={`Ubicación ${selectedDriver?.name || selectedDriver?.nombre || 'inicial'} del repartidor`}
              icon={{
                path: window.google.maps.SymbolPath.CIRCLE,
                scale: 11,
                fillColor: '#22c55e',
                fillOpacity: 1,
                strokeColor: '#ffffff',
                strokeWeight: 2,
              }}
              draggable={Boolean(isAdminMode && selectedDriver)}
              onDragEnd={(event) => {
                if (!onDriverLocationDraftChange) return;
                const nextLat = event?.latLng?.lat?.();
                const nextLng = event?.latLng?.lng?.();
                if (!Number.isFinite(nextLat) || !Number.isFinite(nextLng)) return;
                onDriverLocationDraftChange({ lat: nextLat, lng: nextLng });
              }}
            />

            {demandCenter?.lat !== null && demandCenter?.lng !== null && (
              <>
                <CircleF
                  center={demandCenter}
                  radius={Number(coverageRecommendation?.radio_maximo_km || 0) * 1000}
                  options={{
                    strokeColor: '#22c55e',
                    strokeOpacity: 0.7,
                    strokeWeight: 2,
                    fillColor: '#22c55e',
                    fillOpacity: 0.08,
                  }}
                />
                <MarkerF
                  position={demandCenter}
                  label={{ text: 'C', color: '#ffffff', fontWeight: '900' }}
                  title="Centro recomendado de demanda"
                  onClick={() => setActiveOrder({
                    id: 'centro-demanda',
                    customer: 'Centro recomendado',
                    destination: coverageRecommendation?.mensaje || 'Centro de demanda',
                    position: demandCenter,
                  })}
                />
              </>
            )}

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

            {visiblePendingOrders.map((order) => {
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

            {routeStopMarkers.map((stop) => (
              <MarkerF
                key={`route-stop-${stop.id}`}
                position={stop.position}
                label={{
                  text: String(stop.orden || stop.pedidoId || ''),
                  color: '#ffffff',
                  fontWeight: '800',
                }}
                title={`Ruta #${stop.routeId || stop.routeIndex + 1} - Pedido #${stop.pedidoId}`}
                onClick={() => setActiveOrder(stop)}
                icon={{
                  path: window.google.maps.SymbolPath.CIRCLE,
                  scale: 12,
                  fillColor: ROUTE_COLORS[stop.routeIndex % ROUTE_COLORS.length],
                  fillOpacity: 1,
                  strokeColor: '#ffffff',
                  strokeWeight: 2,
                }}
              />
            ))}

            {diagnosticDriverMarkers.map((driver) => (
              <MarkerF
                key={`driver-diagnostic-${driver.id}`}
                position={driver.position}
                label={{
                  text: 'D',
                  color: '#ffffff',
                  fontWeight: '900',
                }}
                title={`${driver.nombre}: ${driver.motivo}`}
                icon={{
                  path: window.google.maps.SymbolPath.CIRCLE,
                  scale: 10,
                  fillColor: driver.apto ? '#16a34a' : driver.isOutsideRadius ? '#dc2626' : '#f59e0b',
                  fillOpacity: 1,
                  strokeColor: '#ffffff',
                  strokeWeight: 2,
                }}
                onClick={() => setActiveOrder({
                  id: `driver-${driver.id}`,
                  customer: driver.nombre,
                  destination: driver.mensaje_activacion
                    || `${driver.motivo}${driver.distancia_al_centro_demanda_km ? ` (${driver.distancia_al_centro_demanda_km} km)` : ''}`,
                  position: driver.position,
                })}
              />
            ))}

            {outsideRadiusRecommendedMarkers.map((marker) => (
              <MarkerF
                key={`driver-recommended-${marker.id}`}
                position={marker.position}
                label={{
                  text: 'S',
                  color: '#0f172a',
                  fontWeight: '900',
                }}
                title={`Zona sugerida para ${marker.nombre}`}
                icon={{
                  path: window.google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
                  scale: 5,
                  fillColor: '#fde047',
                  fillOpacity: 1,
                  strokeColor: '#0f172a',
                  strokeWeight: 1.5,
                }}
                onClick={() => setActiveOrder({
                  id: `driver-recommended-${marker.id}`,
                  customer: `Zona sugerida ${marker.nombre}`,
                  destination: marker.message || marker.zona || 'Mover repartidor a esta zona para habilitar optimizacion.',
                  position: marker.position,
                })}
              />
            ))}

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
