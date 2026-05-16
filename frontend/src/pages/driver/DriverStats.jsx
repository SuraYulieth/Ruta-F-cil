import { useCallback, useEffect, useState } from 'react';
import { useAppContext } from '../../context/AppContext';
import { api } from '../../services/api';

export const DriverStats = () => {
  const { token } = useAppContext();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      const orders = await api.getMyOrders('');
      const driverInfo = await api.getMyDriverInfo();

      // Calcular estadísticas
      const todayOrders = orders.pedidos || [];
      const completedToday = todayOrders.filter((o) => o.estado === 'Entregado').length;
      const pendingToday = todayOrders.filter((o) => o.estado === 'Asignado' || o.estado === 'En ruta').length;

      setStats({
        totalOrders: todayOrders.length,
        completed: completedToday,
        pending: pendingToday,
        disponible: driverInfo.disponible,
        ultimaConexion: driverInfo.ultima_conexion,
        latitud: driverInfo.latitud_actual,
        longitud: driverInfo.longitud_actual,
      });
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
    loadStats();
    // Actualizar estadísticas cada 60 segundos
    const interval = setInterval(loadStats, 60000);
    return () => clearInterval(interval);
  }, [token, loadStats]);

  const getCompletionPercentage = () => {
    if (!stats || stats.totalOrders === 0) return 0;
    return Math.round((stats.completed / stats.totalOrders) * 100);
  };

  return (
    <div className="driver-stats">
      <div className="stats-header">
        <h2>📊 Estadísticas del Día</h2>
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <div className="loading-state">Cargando estadísticas...</div>
      ) : stats ? (
        <div className="stats-grid">
          {/* Card 1: Total de pedidos */}
          <div className="stat-card primary">
            <div className="stat-icon">📦</div>
            <div className="stat-content">
              <h4>Total de Pedidos</h4>
              <p className="stat-value">{stats.totalOrders}</p>
              <p className="stat-subtitle">Asignados hoy</p>
            </div>
          </div>

          {/* Card 2: Entregados */}
          <div className="stat-card success">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <h4>Entregados</h4>
              <p className="stat-value">{stats.completed}</p>
              <p className="stat-subtitle">{getCompletionPercentage()}% completado</p>
            </div>
          </div>

          {/* Card 3: Pendientes */}
          <div className="stat-card warning">
            <div className="stat-icon">⏳</div>
            <div className="stat-content">
              <h4>Pendientes</h4>
              <p className="stat-value">{stats.pending}</p>
              <p className="stat-subtitle">En proceso</p>
            </div>
          </div>

          {/* Card 4: Estado */}
          <div className={`stat-card ${stats.disponible ? 'info' : 'danger'}`}>
            <div className="stat-icon">{stats.disponible ? '🟢' : '🔴'}</div>
            <div className="stat-content">
              <h4>Estado</h4>
              <p className="stat-value">{stats.disponible ? 'Disponible' : 'No Disponible'}</p>
              <p className="stat-subtitle">Para nuevos pedidos</p>
            </div>
          </div>
        </div>
      ) : null}

      {/* Barra de progreso */}
      {stats && stats.totalOrders > 0 && (
        <div className="progress-section">
          <div className="progress-header">
            <h4>Progreso del Día</h4>
            <span className="progress-text">
              {stats.completed} de {stats.totalOrders}
            </span>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${getCompletionPercentage()}%` }}
            ></div>
          </div>
          <div className="progress-labels">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>
      )}

      {/* Información adicional */}
      {stats && (
        <div className="additional-info">
          <div className="info-row">
            <span className="label">Última conexión:</span>
            <span className="value">
              {stats.ultimaConexion 
                ? new Date(stats.ultimaConexion).toLocaleString('es-CO')
                : 'N/A'}
            </span>
          </div>
          <div className="info-row">
            <span className="label">Ubicación:</span>
            <span className="value">
              {stats.latitud && stats.longitud
                ? `${stats.latitud.toFixed(4)}°, ${stats.longitud.toFixed(4)}°`
                : 'No disponible'}
            </span>
          </div>
        </div>
      )}

      <style>{`
        .driver-stats {
          padding: 20px;
        }
        .stats-header {
          margin-bottom: 24px;
        }
        .stats-header h2 {
          margin: 0;
          color: #333;
        }
        .error-message {
          padding: 12px 16px;
          background: #ffebee;
          color: #c62828;
          border-radius: 4px;
          margin-bottom: 16px;
        }
        .loading-state {
          text-align: center;
          padding: 40px 20px;
          color: #666;
        }
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }
        .stat-card {
          border-radius: 8px;
          padding: 20px;
          display: flex;
          gap: 16px;
          color: white;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          transition: transform 0.2s;
        }
        .stat-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .stat-card.primary {
          background: linear-gradient(135deg, #1976d2, #1565c0);
        }
        .stat-card.success {
          background: linear-gradient(135deg, #388e3c, #2e7d32);
        }
        .stat-card.warning {
          background: linear-gradient(135deg, #f57c00, #e65100);
        }
        .stat-card.info {
          background: linear-gradient(135deg, #00bcd4, #0097a7);
        }
        .stat-card.danger {
          background: linear-gradient(135deg, #d32f2f, #c62828);
        }
        .stat-icon {
          font-size: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 50px;
        }
        .stat-content {
          flex: 1;
        }
        .stat-content h4 {
          margin: 0 0 8px 0;
          font-size: 14px;
          opacity: 0.9;
        }
        .stat-value {
          margin: 0;
          font-size: 28px;
          font-weight: bold;
        }
        .stat-subtitle {
          margin: 4px 0 0 0;
          font-size: 12px;
          opacity: 0.8;
        }
        .progress-section {
          background: white;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .progress-header h4 {
          margin: 0;
          color: #333;
        }
        .progress-text {
          font-size: 14px;
          color: #666;
          font-weight: 600;
        }
        .progress-bar {
          height: 8px;
          background: #e0e0e0;
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 8px;
        }
        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #388e3c, #66bb6a);
          border-radius: 4px;
          transition: width 0.3s ease;
        }
        .progress-labels {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          color: #999;
        }
        .additional-info {
          background: white;
          border-radius: 8px;
          padding: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .info-row {
          display: flex;
          justify-content: space-between;
          padding: 8px 0;
          border-bottom: 1px solid #f0f0f0;
        }
        .info-row:last-child {
          border-bottom: none;
        }
        .info-row .label {
          font-weight: 600;
          color: #666;
        }
        .info-row .value {
          color: #333;
          text-align: right;
        }
      `}</style>
    </div>
  );
};
