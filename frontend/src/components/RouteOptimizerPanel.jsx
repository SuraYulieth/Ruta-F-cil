import { useEffect, useMemo, useState } from 'react';
import { useAppContext } from '../context/AppContext';
import { RouteStopsList } from './RouteStopsList';
import { RouteSummary } from './RouteSummary';

const normalizeText = (value) => String(value || '').trim().toLowerCase();
const isDriverRole = (driver) => ['driver', 'repartidor'].includes(normalizeText(driver?.role));
const isAvailableStatus = (driver) => ['disponible', 'activo', 'active', 'available']
  .includes(normalizeText(driver?.status || driver?.estado));
const getDriverCoordinates = (driver) => {
  const lat = driver?.latitud_actual ?? driver?.latitud ?? driver?.latitude;
  const lng = driver?.longitud_actual ?? driver?.longitud ?? driver?.longitude;
  const parsedLat = Number(lat);
  const parsedLng = Number(lng);
  if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLng)) return null;
  return { lat: parsedLat, lng: parsedLng };
};
const getOptimizerHiddenReason = (driver) => {
  if (!isDriverRole(driver)) return 'Rol no habilitado para reparto';
  if (driver?.disponible !== true) return 'No disponible';
  if (!isAvailableStatus(driver)) return 'Estado inactivo';
  if (!getDriverCoordinates(driver)) return 'Sin coordenadas';
  return '';
};
const isAvailableForOptimization = (driver) => (
  isDriverRole(driver)
  && driver?.disponible === true
  && isAvailableStatus(driver)
  && Boolean(getDriverCoordinates(driver))
);

export const RouteOptimizerPanel = ({ onDriverLocationChange, onOptimized }) => {
  const { getDrivers, orders, optimizeRoute, assignOptimizedRoute } = useAppContext();
  const drivers = Array.isArray(getDrivers?.()) ? getDrivers() : [];
  const availableDrivers = useMemo(
    () => drivers.filter(isAvailableForOptimization),
    [drivers],
  );
  const hiddenDrivers = useMemo(
    () => drivers
      .filter((driver) => isDriverRole(driver) && !isAvailableForOptimization(driver))
      .map((driver) => ({
        id: driver.id,
        name: driver.name || driver.nombre || `Driver ${driver.id}`,
        reason: getOptimizerHiddenReason(driver),
      })),
    [drivers],
  );
  const safeOrders = Array.isArray(orders) ? orders : [];
  const pendingOrders = safeOrders.filter(
    (order) => String(order.estado || order.status || '').toLowerCase() === 'pendiente'
  );
  const firstDriver = availableDrivers[0];

  const [driverId, setDriverId] = useState(firstDriver?.id || '');
  const [routeMode, setRouteMode] = useState('multi_ruta');
  const [lat, setLat] = useState('4.7110');
  const [lng, setLng] = useState('-74.0721');
  const [capacity, setCapacity] = useState('15');
  const [maxDurationMins, setMaxDurationMins] = useState('90');
  const [maxAreaKm2, setMaxAreaKm2] = useState('382');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [optimization, setOptimization] = useState(null);
  const [error, setError] = useState('');

  const selectedOrderIds = useMemo(
    () => optimization?.optimizer?.pedidos_seleccionados || [],
    [optimization],
  );
  const createdRoutes = optimization?.optimizer?.routes || [];

  useEffect(() => {
    if (!driverId && firstDriver?.id) {
      setDriverId(firstDriver.id);
    }
  }, [driverId, firstDriver]);

  useEffect(() => {
    const selectedDriver = availableDrivers.find((driver) => Number(driver.id) === Number(driverId));
    const coords = selectedDriver ? getDriverCoordinates(selectedDriver) : null;
    if (coords && (String(coords.lat) !== String(lat) || String(coords.lng) !== String(lng))) {
      setLat(String(coords.lat));
      setLng(String(coords.lng));
    }
  }, [driverId, availableDrivers, lat, lng]);

  useEffect(() => {
    onDriverLocationChange?.({
      lat: Number(lat),
      lng: Number(lng),
    });
  }, [lat, lng, onDriverLocationChange]);

  const handleOptimize = async () => {
    setError('');
    if (!Number.isFinite(Number(lat)) || !Number.isFinite(Number(lng))) {
      setError('La ubicacion inicial del repartidor debe tener latitud y longitud validas.');
      return;
    }
    if (!Number.isFinite(Number(capacity)) || Number(capacity) <= 0) {
      setError('La capacidad maxima debe ser un numero mayor que cero.');
      return;
    }

    setIsOptimizing(true);
    try {
      const result = await optimizeRoute({
        modo: routeMode,
        repartidor_id: driverId ? Number(driverId) : undefined,
        latitud_inicio: Number(lat),
        longitud_inicio: Number(lng),
        pedidos_candidatos: pendingOrders.map((order) => order.id),
        capacidad_maxima_kg: Number(capacity),
        max_duration_mins: Number(maxDurationMins),
        max_area_km2: Number(maxAreaKm2),
        reglas_negocio: { max_orders: 6 },
      });
      setOptimization(result);
      onOptimized?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleAssign = async () => {
    if (routeMode === 'multi_ruta' || !optimization?.route?.id) return;
    setIsAssigning(true);
    try {
      const route = await assignOptimizedRoute(optimization.route.id);
      setOptimization((current) => ({ ...current, route }));
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAssigning(false);
    }
  };

  return (
    <section className="panel route-optimizer-panel">
      <div className="panel-title-row">
        <h2>Optimizador de ruta</h2>
        <span className="count">{pendingOrders.length}</span>
      </div>

      <div className="optimizer-controls">
        <label>
          Modo
          <select value={routeMode} onChange={(event) => setRouteMode(event.target.value)}>
            <option value="ruta_unica">Ruta única</option>
            <option value="multi_ruta">Multi ruta</option>
          </select>
        </label>

        <label>
          Repartidor
          <select value={driverId} onChange={(event) => setDriverId(event.target.value)}>
            <option value="">Automatico</option>
            {availableDrivers.map((driver) => (
              <option key={driver.id} value={driver.id}>{driver.name || driver.nombre || `Driver ${driver.id}`}</option>
            ))}
          </select>
        </label>

        {hiddenDrivers.length > 0 && (
          <details className="optimizer-driver-debug">
            <summary>Ver diagnostico tecnico</summary>
            {hiddenDrivers.slice(0, 3).map((driver) => (
              <p key={driver.id}>{driver.name}: {driver.reason}</p>
            ))}
          </details>
        )}

        <label>
          Latitud inicial
          <input value={lat} onChange={(event) => setLat(event.target.value)} />
        </label>

        <label>
          Longitud inicial
          <input value={lng} onChange={(event) => setLng(event.target.value)} />
        </label>

        <label>
          Capacidad kg
          <input value={capacity} onChange={(event) => setCapacity(event.target.value)} />
        </label>

        <label>
          Duración máx. min
          <input value={maxDurationMins} onChange={(event) => setMaxDurationMins(event.target.value)} />
        </label>

        <label>
          Área máx. km²
          <input value={maxAreaKm2} onChange={(event) => setMaxAreaKm2(event.target.value)} />
        </label>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="actions split-actions">
        <button
          className="btn-primary"
          onClick={handleOptimize}
          disabled={isOptimizing || pendingOrders.length === 0}
        >
          {isOptimizing ? 'Optimizando...' : 'Optimizar ruta'}
        </button>
        <button
          className="btn-secondary"
          onClick={handleAssign}
          disabled={isAssigning || routeMode === 'multi_ruta' || !optimization?.route?.id}
        >
          {routeMode === 'multi_ruta' ? 'Asignación automática' : isAssigning ? 'Asignando...' : 'Asignar ruta'}
        </button>
      </div>

      <RouteSummary optimization={optimization} />
      <RouteStopsList optimization={optimization} />

      {selectedOrderIds.length > 0 && (
        <p className="hint-text">Pedidos seleccionados: {selectedOrderIds.join(', ')}</p>
      )}

      {createdRoutes.length > 1 && (
        <p className="hint-text">Se generaron {createdRoutes.length} rutas en esta optimización.</p>
      )}
    </section>
  );
};
