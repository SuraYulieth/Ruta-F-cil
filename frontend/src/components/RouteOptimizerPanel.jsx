import { useEffect, useMemo, useRef, useState } from 'react';
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
const getDriverProfileId = (driver) => driver?.profile_id || driver?.repartidor_id || driver?.id;

export const RouteOptimizerPanel = ({
  onDriverLocationChange,
  onOptimized,
  externalDriverLocation,
  onSelectedDriverChange,
}) => {
  const {
    getDrivers,
    orders,
    optimizeRoute,
    assignOptimizedRoute,
    updateDriverLocation,
  } = useAppContext();

  const drivers = Array.isArray(getDrivers?.()) ? getDrivers() : [];
  const driverCandidates = useMemo(
    () => drivers.filter(isDriverRole),
    [drivers],
  );

  const safeOrders = Array.isArray(orders) ? orders : [];
  const pendingOrders = safeOrders.filter(
    (order) => String(order.estado || order.status || '').toLowerCase() === 'pendiente'
  );

  const firstDriver = driverCandidates[0];

  const [driverId, setDriverId] = useState(firstDriver?.id || '');
  const [routeMode, setRouteMode] = useState('multi_ruta');
  const [lat, setLat] = useState('4.7110');
  const [lng, setLng] = useState('-74.0721');
  const [capacity, setCapacity] = useState('15');
  const [maxDurationMins, setMaxDurationMins] = useState('90');
  const [maxAreaKm2, setMaxAreaKm2] = useState('382');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isSavingLocation, setIsSavingLocation] = useState(false);
  const [optimization, setOptimization] = useState(null);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const lastNotifiedDriverIdRef = useRef(null);

  const selectedDriver = useMemo(
    () => driverCandidates.find((driver) => Number(driver.id) === Number(driverId)) || null,
    [driverCandidates, driverId],
  );
  const selectedDriverCoords = selectedDriver ? getDriverCoordinates(selectedDriver) : null;

  const selectedOrderIds = useMemo(
    () => optimization?.optimizer?.pedidos_seleccionados || [],
    [optimization],
  );
  const createdRoutes = optimization?.optimizer?.routes || [];

  const parsedLat = Number(lat);
  const parsedLng = Number(lng);
  const hasValidDraftCoordinates = Number.isFinite(parsedLat) && Number.isFinite(parsedLng);
  const hasUnsavedLocationChange = useMemo(() => {
    if (!selectedDriver || !hasValidDraftCoordinates) return false;
    if (!selectedDriverCoords) return true;
    return parsedLat !== selectedDriverCoords.lat || parsedLng !== selectedDriverCoords.lng;
  }, [selectedDriver, hasValidDraftCoordinates, selectedDriverCoords, parsedLat, parsedLng]);

  useEffect(() => {
    if (!driverId && firstDriver?.id) {
      setDriverId(firstDriver.id);
    }
  }, [driverId, firstDriver]);

  useEffect(() => {
    const selectedId = selectedDriver ? Number(selectedDriver.id) : null;
    if (lastNotifiedDriverIdRef.current === selectedId) return;
    lastNotifiedDriverIdRef.current = selectedId;
    onSelectedDriverChange?.(selectedDriver);
  }, [selectedDriver?.id, onSelectedDriverChange]);

  useEffect(() => {
    if (!selectedDriver) return;
    const coords = getDriverCoordinates(selectedDriver);
    if (!coords) return;

    const nextLat = String(coords.lat);
    const nextLng = String(coords.lng);
    if (nextLat !== String(lat)) setLat(nextLat);
    if (nextLng !== String(lng)) setLng(nextLng);
  }, [selectedDriver]);

  useEffect(() => {
    const externalLat = Number(externalDriverLocation?.lat);
    const externalLng = Number(externalDriverLocation?.lng);
    if (!Number.isFinite(externalLat) || !Number.isFinite(externalLng)) return;

    if (String(externalLat) !== String(lat)) setLat(String(externalLat));
    if (String(externalLng) !== String(lng)) setLng(String(externalLng));
  }, [externalDriverLocation]);

  useEffect(() => {
    if (!hasValidDraftCoordinates) return;
    onDriverLocationChange?.({
      lat: parsedLat,
      lng: parsedLng,
    });
  }, [parsedLat, parsedLng, hasValidDraftCoordinates, onDriverLocationChange]);

  const optimizeWithCurrentDraft = async () => {
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
    return result;
  };

  const handleOptimize = async () => {
    setError('');
    setSuccessMessage('');

    if (!hasValidDraftCoordinates) {
      setError('La ubicación inicial del repartidor debe tener latitud y longitud válidas.');
      return;
    }
    if (!Number.isFinite(Number(capacity)) || Number(capacity) <= 0) {
      setError('La capacidad máxima debe ser un número mayor que cero.');
      return;
    }

    setIsOptimizing(true);
    try {
      await optimizeWithCurrentDraft();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleUpdateDriverLocation = async () => {
    if (!selectedDriver) {
      setError('Selecciona un repartidor antes de actualizar su ubicación.');
      return;
    }
    if (!hasValidDraftCoordinates) {
      setError('La latitud y longitud deben ser valores válidos.');
      return;
    }

    const driverProfileId = getDriverProfileId(selectedDriver);
    if (!driverProfileId) {
      setError('No se encontró el identificador del perfil del repartidor.');
      return;
    }

    setError('');
    setSuccessMessage('');
    setIsSavingLocation(true);
    try {
      await updateDriverLocation(Number(driverProfileId), parsedLat, parsedLng);
      if (pendingOrders.length > 0) {
        await optimizeWithCurrentDraft();
      }
      setSuccessMessage('Ubicación del repartidor actualizada correctamente y diagnóstico recalculado.');
    } catch (err) {
      setError(err.message || 'No se pudo actualizar la ubicación del repartidor.');
    } finally {
      setIsSavingLocation(false);
    }
  };

  const handleUseCurrentBrowserLocation = () => {
    setError('');
    if (!navigator?.geolocation) {
      setError('Este navegador no soporta geolocalización.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(String(position.coords.latitude));
        setLng(String(position.coords.longitude));
      },
      () => {
        setError('No fue posible obtener tu ubicación actual.');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
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

  const driverName = selectedDriver?.name || selectedDriver?.nombre || 'Sin selección';
  const isAvailable = selectedDriver?.disponible === true;
  const hasCoordinates = Boolean(selectedDriverCoords);
  const isInsideRadius = !selectedDriver?.distancia_al_centro_demanda_km
    || Number(selectedDriver?.distancia_al_centro_demanda_km) <= Number(selectedDriver?.radio_maximo_km || 0);
  const hasActiveRoute = normalizeText(selectedDriver?.status || selectedDriver?.estado) === 'ocupado';
  const canTakeOrders = isAvailable
    && isAvailableStatus(selectedDriver)
    && !hasActiveRoute
    && hasCoordinates
    && isInsideRadius;

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
            <option value="">Automático</option>
            {driverCandidates.map((driver) => (
              <option key={driver.id} value={driver.id}>
                {driver.name || driver.nombre || `Driver ${driver.id}`}
              </option>
            ))}
          </select>
        </label>

        <label>
          Latitud para optimizar
          <input value={lat} onChange={(event) => setLat(event.target.value)} />
        </label>

        <label>
          Longitud para optimizar
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

      {selectedDriver && (
        <div className="coverage-recommendation-card mt-4">
          <h3>Repartidor seleccionado: {driverName}</h3>
          <p>
            Ubicación actual: {hasCoordinates ? `Lat ${selectedDriverCoords.lat}, Lng ${selectedDriverCoords.lng}` : 'Sin coordenadas registradas'}
          </p>
          <p>
            Ubicación para optimizar: {hasValidDraftCoordinates ? `Lat ${parsedLat}, Lng ${parsedLng}` : 'Coordenadas inválidas'}
          </p>
          <div className="coverage-recommendation-metrics">
            <span>Estado: <strong>{selectedDriver.status || selectedDriver.estado || 'Sin estado'}</strong></span>
            <span>{isAvailable ? 'Disponible' : 'No disponible'}</span>
            <span>{hasCoordinates ? 'Tiene coordenadas' : 'Sin coordenadas'}</span>
            <span>{isInsideRadius ? 'Dentro del radio' : 'Fuera del radio'}</span>
          </div>
          {!canTakeOrders && (
            <p className="warning-text">
              {driverName} no puede tomar pedidos porque {hasActiveRoute
                ? 'tiene una ruta activa.'
                : !isAvailable
                  ? 'está no disponible.'
                  : !hasCoordinates
                    ? 'no tiene coordenadas válidas.'
                    : !isInsideRadius
                      ? 'está fuera del radio.'
                      : 'no cumple el estado operativo requerido.'}
              {!isInsideRadius && ' Actualiza su ubicación cerca del centro recomendado.'}
            </p>
          )}
        </div>
      )}

      {hasUnsavedLocationChange && selectedDriver && (
        <div className="warning-message mt-4">
          Cambiaste la ubicación inicial, pero no has actualizado el perfil del repartidor.
        </div>
      )}

      {error && <div className="error-message mt-4">{error}</div>}
      {successMessage && <div className="success-message mt-4">{successMessage}</div>}

      <div className="actions split-actions mt-4">
        <button
          className="btn-secondary"
          onClick={handleUpdateDriverLocation}
          disabled={!selectedDriver || !hasValidDraftCoordinates || isSavingLocation}
        >
          {isSavingLocation ? 'Actualizando ubicación...' : 'Actualizar ubicación del repartidor'}
        </button>
        <button className="btn-secondary" onClick={handleUseCurrentBrowserLocation}>
          Usar mi ubicación actual
        </button>
      </div>

      <div className="actions split-actions mt-4">
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
