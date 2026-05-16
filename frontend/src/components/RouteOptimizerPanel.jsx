import { useEffect, useMemo, useState } from 'react';
import { useAppContext } from '../context/AppContext';
import { RouteStopsList } from './RouteStopsList';
import { RouteSummary } from './RouteSummary';

export const RouteOptimizerPanel = ({ onDriverLocationChange, onOptimized }) => {
  const { getDrivers, orders, optimizeRoute, assignOptimizedRoute } = useAppContext();
  const drivers = Array.isArray(getDrivers?.()) ? getDrivers() : [];
  const safeOrders = Array.isArray(orders) ? orders : [];
  const pendingOrders = safeOrders.filter(
    (order) => String(order.estado || order.status || '').toLowerCase() === 'pendiente'
  );
  const firstDriver = drivers.find((driver) => String(driver.status || driver.estado || '').toLowerCase() === 'disponible') || drivers[0];

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
            {drivers.map((driver) => (
              <option key={driver.id} value={driver.id}>{driver.name || driver.nombre || `Driver ${driver.id}`}</option>
            ))}
          </select>
        </label>

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
