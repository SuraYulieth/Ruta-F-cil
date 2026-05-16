import { useEffect, useMemo, useState } from 'react';
import { useAppContext } from '../context/AppContext';
import { RouteStopsList } from './RouteStopsList';
import { RouteSummary } from './RouteSummary';

export const RouteOptimizerPanel = ({ onDriverLocationChange, onOptimized }) => {
  const { getDrivers, orders, optimizeRoute, assignOptimizedRoute } = useAppContext();
  const drivers = getDrivers();
  const pendingOrders = orders.filter((order) => order.status === 'Pendiente' || order.estado === 'Pendiente');
  const firstDriver = drivers.find((driver) => driver.status === 'Disponible') || drivers[0];

  const [driverId, setDriverId] = useState(firstDriver?.id || '');
  const [lat, setLat] = useState('4.7110');
  const [lng, setLng] = useState('-74.0721');
  const [capacity, setCapacity] = useState('15');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [optimization, setOptimization] = useState(null);
  const [error, setError] = useState('');

  const selectedOrderIds = useMemo(
    () => optimization?.optimizer?.pedidos_seleccionados || [],
    [optimization],
  );

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
        repartidor_id: Number(driverId),
        latitud_inicio: Number(lat),
        longitud_inicio: Number(lng),
        pedidos_candidatos: pendingOrders.map((order) => order.id),
        capacidad_maxima_kg: Number(capacity),
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
    if (!optimization?.route?.id) return;
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
          Repartidor
          <select value={driverId} onChange={(event) => setDriverId(event.target.value)}>
            {drivers.map((driver) => (
              <option key={driver.id} value={driver.id}>{driver.name}</option>
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
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="actions split-actions">
        <button
          className="btn-primary"
          onClick={handleOptimize}
          disabled={isOptimizing || !driverId || pendingOrders.length === 0}
        >
          {isOptimizing ? 'Optimizando...' : 'Optimizar ruta'}
        </button>
        <button
          className="btn-secondary"
          onClick={handleAssign}
          disabled={isAssigning || !optimization?.route?.id}
        >
          {isAssigning ? 'Asignando...' : 'Asignar ruta'}
        </button>
      </div>

      <RouteSummary optimization={optimization} />
      <RouteStopsList optimization={optimization} />

      {selectedOrderIds.length > 0 && (
        <p className="hint-text">Pedidos seleccionados: {selectedOrderIds.join(', ')}</p>
      )}
    </section>
  );
};
