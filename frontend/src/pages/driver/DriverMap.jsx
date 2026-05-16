import { useCallback, useEffect, useState } from 'react';
import { useAppContext } from '../../context/AppContext';
import { api } from '../../services/api';
import { startDriverLocationTracking, stopDriverLocationTracking } from '../../services/geolocation';

// Componente placeholder para mapa. Integración real con Google Maps/Leaflet pendiente
export const DriverMap = () => {
  const { token } = useAppContext();
  const [routes, setRoutes] = useState([]);
  const [currentLocation, setCurrentLocation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadRouteData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getMyRoutes('');
      setRoutes(data.rutas || []);
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const getCurrentPosition = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocalización no soportada por este navegador');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCurrentLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: new Date(position.timestamp),
        });
      },
      (err) => {
        console.error('Error geolocation:', err);
        setError('No se pudo obtener la ubicación actual');
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      },
    );
  }, []);

  useEffect(() => {
    if (!token) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadRouteData();
    getCurrentPosition();

    const watchId = startDriverLocationTracking({
      onPosition: (position) => {
        setCurrentLocation({
          lat: position.lat,
          lng: position.lng,
          accuracy: position.accuracy,
          timestamp: new Date(position.timestamp),
        });
      },
      onError: (err) => {
        setError(err.message);
      },
    });

    // Auto refresh cada 30 segundos
    const interval = setInterval(() => {
      loadRouteData();
    }, 30000);

    return () => {
      clearInterval(interval);
      stopDriverLocationTracking(watchId);
    };
  }, [token, loadRouteData, getCurrentPosition]);

  const getRouteStatusBadge = (status) => {
    const map = {
      'Planificada': 'badge-planned',
      'En curso': 'badge-active',
      'Completada': 'badge-completed',
      'Cancelada': 'badge-cancelled',
    };
    return map[status] || 'badge-default';
  };

  return (
    <div className="driver-map">
      <div className="map-header">
        <h2>🗺️ Mi Ruta en Mapa</h2>
        <button onClick={getCurrentPosition} className="btn-refresh">
          🔄 Actualizar Ubicación
        </button>
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {/* Panel de ubicación actual */}
      <div className="location-panel">
        <h3>📍 Ubicación Actual</h3>
        {currentLocation ? (
          <div className="location-info">
            <p><strong>Latitud:</strong> {currentLocation.lat.toFixed(6)}</p>
            <p><strong>Longitud:</strong> {currentLocation.lng.toFixed(6)}</p>
            <p><strong>Precisión:</strong> ±{Math.round(currentLocation.accuracy)}m</p>
            <p><strong>Hora:</strong> {currentLocation.timestamp.toLocaleTimeString('es-CO')}</p>
          </div>
        ) : (
          <p className="text-muted">Obteniendo ubicación...</p>
        )}
      </div>

      {/* Mapa placeholder */}
      <div className="map-placeholder">
        <div className="map-content">
          <div className="map-icon">🗺️</div>
          <h3>Mapa Interactivo</h3>
          <p>Integración con Google Maps/Leaflet pendiente</p>
          {currentLocation && (
            <div className="coordinates">
              <code>{currentLocation.lat.toFixed(4)}, {currentLocation.lng.toFixed(4)}</code>
            </div>
          )}
        </div>
      </div>

      {/* Lista de rutas */}
      <div className="routes-section">
        <h3>🛣️ Mis Rutas Asignadas ({routes.length})</h3>
        {loading ? (
          <div className="loading">Cargando rutas...</div>
        ) : routes.length === 0 ? (
          <div className="empty-state">No tienes rutas asignadas</div>
        ) : (
          <div className="routes-list">
            {routes.map((route) => (
              <div key={route.id} className="route-card">
                <div className="route-header">
                  <h4>Ruta #{route.id}</h4>
                  <span className={`badge ${getRouteStatusBadge(route.estado_ruta)}`}>
                    {route.estado_ruta}
                  </span>
                </div>
                <div className="route-details">
                  <p><strong>Fecha:</strong> {route.fecha ? new Date(route.fecha).toLocaleDateString('es-CO') : 'N/A'}</p>
                  <p><strong>Paradas:</strong> {route.total_paradas || route.paradas?.length || 0}</p>
                  <p><strong>Distancia:</strong> {route.distancia_total_km ? `${route.distancia_total_km} km` : 'N/A'}</p>
                </div>
                {route.paradas && route.paradas.length > 0 && (
                  <details className="stops-details">
                    <summary>Ver paradas ({route.paradas.length})</summary>
                    <ul>
                      {route.paradas.slice(0, 5).map((stop, idx) => (
                        <li key={stop.id || idx}>
                          #{stop.orden || idx + 1} - {stop.direccion || `Lat: ${stop.latitud}, Lng: ${stop.longitud}`}
                        </li>
                      ))}
                      {route.paradas.length > 5 && (
                        <li>... y {route.paradas.length - 5} paradas más</li>
                      )}
                    </ul>
                  </details>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        .driver-map {
          padding: 20px;
        }
        .map-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }
        .btn-refresh {
          padding: 8px 16px;
          background: #1976d2;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        }
        .btn-refresh:hover {
          background: #1565c0;
        }
        .error-message {
          padding: 12px 16px;
          background: #ffebee;
          color: #c62828;
          border-radius: 4px;
          margin-bottom: 16px;
        }
        .location-panel {
          background: white;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .location-panel h3 {
          margin-top: 0;
          color: #333;
        }
        .location-info {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 8px;
        }
        .location-info p {
          margin: 4px 0;
          font-size: 14px;
        }
        .map-placeholder {
          height: 300px;
          background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 20px;
          border: 2px dashed #90a4ae;
        }
        .map-content {
          text-align: center;
        }
        .map-icon {
          font-size: 64px;
          margin-bottom: 12px;
        }
        .map-content h3 {
          margin: 8px 0;
          color: #455a64;
        }
        .map-content p {
          color: #607d8b;
          margin: 8px 0;
        }
        .coordinates {
          margin-top: 12px;
        }
        .coordinates code {
          background: rgba(0,0,0,0.1);
          padding: 6px 12px;
          border-radius: 4px;
          font-family: monospace;
          font-size: 14px;
        }
        .routes-section {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .routes-section h3 {
          margin-top: 0;
          margin-bottom: 16px;
          color: #333;
        }
        .routes-list {
          display: grid;
          gap: 12px;
        }
        .route-card {
          border: 1px solid #e0e0e0;
          border-radius: 6px;
          padding: 14px;
          background: #fafafa;
        }
        .route-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }
        .route-header h4 {
          margin: 0;
          color: #333;
        }
        .route-details p {
          margin: 4px 0;
          font-size: 14px;
          color: #666;
        }
        .stops-details {
          margin-top: 10px;
          font-size: 13px;
        }
        .stops-details summary {
          cursor: pointer;
          color: #1976d2;
          font-weight: 600;
        }
        .stops-details ul {
          margin: 8px 0;
          padding-left: 20px;
        }
        .stops-details li {
          margin: 4px 0;
          color: #555;
        }
        .badge {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
        }
        .badge-planned { background: #e3f2fd; color: #1976d2; }
        .badge-active { background: #fff3e0; color: #f57c00; }
        .badge-completed { background: #e8f5e9; color: #388e3c; }
        .badge-cancelled { background: #ffebee; color: #d32f2f; }
        .badge-default { background: #f5f5f5; color: #666; }
        .loading, .empty-state {
          text-align: center;
          padding: 30px;
          color: #999;
        }
        .text-muted {
          color: #999;
        }
      `}</style>
    </div>
  );
};
