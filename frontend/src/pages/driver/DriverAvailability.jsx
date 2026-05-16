import { useCallback, useEffect, useState } from 'react';
import { useAppContext } from '../../context/AppContext';
import { api } from '../../services/api';

export const DriverAvailability = () => {
  const { token, driverProfile, toggleAvailability, loadDriverDashboard } = useAppContext();
  const [driverInfo, setDriverInfo] = useState(null);
  const [disponible, setDisponible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdate, setLastUpdate] = useState(null);

  const loadDriverInfo = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getMyDriverInfo();
      setDriverInfo(data);
      setDisponible(data.disponible || false);
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadDriverInfo();
    // Actualizar info del driver cada 30 segundos
    const interval = setInterval(loadDriverInfo, 30000);
    return () => clearInterval(interval);
  }, [token, loadDriverInfo]);

  const handleToggleAvailability = async () => {
    try {
      setUpdating(true);
      await toggleAvailability();
      setLastUpdate(new Date());
      setError('');
      await loadDriverDashboard();
      await loadDriverInfo();
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdating(false);
    }
  };

  useEffect(() => {
    if (!driverProfile) return;
    setDriverInfo(driverProfile);
    setDisponible(!!driverProfile.disponible);
  }, [driverProfile]);

  return (
    <div className="driver-availability">
      <div className="availability-card">
        <div className="card-header">
          <h3>🚗 Estado de Disponibilidad</h3>
          {lastUpdate && (
            <span className="last-update">
              Actualizado: {lastUpdate.toLocaleTimeString('es-CO')}
            </span>
          )}
        </div>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {loading ? (
          <div className="loading-state">Cargando información...</div>
        ) : (
          <div className="availability-content">
            <div className="status-display">
              <div className={`status-indicator ${disponible ? 'available' : 'unavailable'}`}>
                {disponible ? '🟢' : '🔴'}
              </div>
              <div className="status-text">
                <h4>{disponible ? 'Disponible' : 'No Disponible'}</h4>
                <p>
                  {disponible 
                    ? 'Recibirás nuevos pedidos'
                    : 'No recibirás nuevos pedidos'}
                </p>
              </div>
            </div>

            <div className="info-grid">
              {driverInfo && (
                <>
                  <div className="info-item">
                    <span className="label">Usuario:</span>
                    <span className="value">{driverInfo.nombre}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">Email:</span>
                    <span className="value">{driverInfo.email}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">Última conexión:</span>
                    <span className="value">
                      {driverInfo.ultima_conexion 
                        ? new Date(driverInfo.ultima_conexion).toLocaleString('es-CO')
                        : 'N/A'}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="label">Ubicación actual:</span>
                    <span className="value">
                      {driverInfo.latitud_actual && driverInfo.longitud_actual
                        ? `${driverInfo.latitud_actual.toFixed(4)}, ${driverInfo.longitud_actual.toFixed(4)}`
                        : 'No disponible'}
                    </span>
                  </div>
                </>
              )}
            </div>

            <button
              onClick={handleToggleAvailability}
              disabled={updating}
              className={`toggle-btn ${disponible ? 'btn-set-unavailable' : 'btn-set-available'}`}
            >
              {updating ? 'Actualizando...' : disponible ? '❌ Marcar No Disponible' : '✅ Marcar Disponible'}
            </button>
          </div>
        )}
      </div>

      <style>{`
        .driver-availability {
          padding: 20px;
        }
        .availability-card {
          background: white;
          border-radius: 8px;
          padding: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          max-width: 600px;
        }
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          border-bottom: 2px solid #f0f0f0;
          padding-bottom: 12px;
        }
        .card-header h3 {
          margin: 0;
          color: #333;
        }
        .last-update {
          font-size: 12px;
          color: #999;
        }
        .error-message {
          padding: 12px 16px;
          background: #ffebee;
          color: #c62828;
          border-radius: 4px;
          margin-bottom: 16px;
          font-size: 14px;
        }
        .loading-state {
          text-align: center;
          padding: 40px 20px;
          color: #666;
        }
        .availability-content {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        .status-display {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 20px;
          background: #f9f9f9;
          border-radius: 8px;
        }
        .status-indicator {
          font-size: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 80px;
          height: 80px;
          border-radius: 50%;
          background: white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .status-indicator.available {
          animation: pulse-green 2s infinite;
        }
        .status-indicator.unavailable {
          animation: pulse-red 2s infinite;
        }
        @keyframes pulse-green {
          0%, 100% { box-shadow: 0 0 0 0 rgba(56, 142, 60, 0.7); }
          50% { box-shadow: 0 0 0 10px rgba(56, 142, 60, 0); }
        }
        @keyframes pulse-red {
          0%, 100% { box-shadow: 0 0 0 0 rgba(211, 47, 47, 0.7); }
          50% { box-shadow: 0 0 0 10px rgba(211, 47, 47, 0); }
        }
        .status-text h4 {
          margin: 0 0 4px 0;
          font-size: 18px;
          color: #333;
        }
        .status-text p {
          margin: 0;
          font-size: 14px;
          color: #666;
        }
        .info-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }
        .info-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .info-item .label {
          font-size: 12px;
          font-weight: 600;
          color: #999;
          text-transform: uppercase;
        }
        .info-item .value {
          font-size: 14px;
          color: #333;
          word-break: break-all;
        }
        .toggle-btn {
          padding: 12px 24px;
          border: none;
          border-radius: 4px;
          font-weight: 600;
          font-size: 16px;
          cursor: pointer;
          transition: all 0.3s;
          width: 100%;
        }
        .btn-set-available {
          background: #388e3c;
          color: white;
        }
        .btn-set-available:hover:not(:disabled) {
          background: #2e7d32;
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(56, 142, 60, 0.3);
        }
        .btn-set-unavailable {
          background: #d32f2f;
          color: white;
        }
        .btn-set-unavailable:hover:not(:disabled) {
          background: #c62828;
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(211, 47, 47, 0.3);
        }
        .toggle-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};
