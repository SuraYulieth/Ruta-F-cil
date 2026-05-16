import { useCallback, useEffect, useState } from 'react';
import { useAppContext } from '../../context/AppContext';
import { api } from '../../services/api';

export const DriverOrders = () => {
  const { token, startOrder, deliverOrder, completeOrder } = useAppContext();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedFilter, setSelectedFilter] = useState(''); // Empty = todas

  const loadOrders = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getMyOrders(selectedFilter);
      setOrders(data.pedidos || []);
      setError('');
    } catch (err) {
      setError(err.message);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [selectedFilter]);

  useEffect(() => {
    if (!token) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadOrders();
  }, [token, loadOrders]);

  const handleStartOrder = async (orderId) => {
    try {
      await startOrder(orderId);
      await loadOrders();
    } catch (err) {
      setError(`Error al iniciar: ${err.message}`);
    }
  };

  const handleDeliverOrder = async (orderId) => {
    const comentarios = prompt('¿Algún comentario sobre la entrega?', '');
    if (comentarios === null) return; // Cancelado
    try {
      await deliverOrder(orderId, comentarios);
      await loadOrders();
    } catch (err) {
      setError(`Error al entregar: ${err.message}`);
    }
  };

  const handleCompleteOrder = async (orderId) => {
    try {
      await completeOrder(orderId);
      await loadOrders();
    } catch (err) {
      setError(`Error al completar: ${err.message}`);
    }
  };

  const getEstadoBadgeClass = (estado) => {
    const map = {
      'Pendiente': 'badge-pending',
      'Asignado': 'badge-assigned',
      'En ruta': 'badge-in-progress',
      'Entregado': 'badge-completed',
      'Cancelado': 'badge-cancelled',
    };
    return map[estado] || 'badge-default';
  };

  return (
    <div className="driver-orders">
      <div className="orders-header">
        <h2>📦 Mis Pedidos</h2>
        <div className="filter-group">
          <select 
            value={selectedFilter} 
            onChange={(e) => setSelectedFilter(e.target.value)}
            className="filter-select"
          >
            <option value="">Todos los estados</option>
            <option value="Pendiente">Pendiente</option>
            <option value="Asignado">Asignado</option>
            <option value="En ruta">En ruta</option>
            <option value="Entregado">Entregado</option>
            <option value="Cancelado">Cancelado</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="error-alert">
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <div className="loading">Cargando pedidos...</div>
      ) : orders.length === 0 ? (
        <div className="empty-state">
          <p>No hay pedidos en este estado</p>
        </div>
      ) : (
        <div className="orders-list">
          {orders.map((order) => (
            <div key={order.id} className="order-card">
              <div className="order-header">
                <div className="order-id">
                  <strong>Pedido #{order.id}</strong>
                  <span className={`badge ${getEstadoBadgeClass(order.estado)}`}>
                    {order.estado}
                  </span>
                </div>
                {order.prioridad && (
                  <span className={`priority priority-${order.prioridad.toLowerCase()}`}>
                    🔴 {order.prioridad}
                  </span>
                )}
              </div>

              <div className="order-details">
                <div className="detail-row">
                  <span className="label">👤 Cliente:</span>
                  <span className="value">{order.cliente_nombre || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">📍 Dirección:</span>
                  <span className="value">{order.direccion || 'N/A'}</span>
                </div>
                {order.ruta_id && (
                  <div className="detail-row">
                    <span className="label">🛣️ Ruta:</span>
                    <span className="value">#{order.ruta_id}</span>
                  </div>
                )}
              </div>

              <div className="order-actions">
                {order.estado === 'Asignado' && (
                  <button 
                    onClick={() => handleStartOrder(order.id)}
                    className="btn-primary"
                  >
                    ▶️ Iniciar Entrega
                  </button>
                )}
                {order.estado === 'En ruta' && (
                  <button 
                    onClick={() => handleDeliverOrder(order.id)}
                    className="btn-success"
                  >
                    ✅ Marcar Entregado
                  </button>
                )}
                {order.estado === 'Entregado' && (
                  <span className="badge-completed">✓ Completado</span>
                )}
                {order.estado !== 'Entregado' && (
                  <button
                    onClick={() => handleCompleteOrder(order.id)}
                    className="btn-secondary"
                  >
                    Completar pedido
                  </button>
                )}
                {order.estado === 'Pendiente' && (
                  <span className="text-muted">Esperando asignación...</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .driver-orders {
          padding: 20px;
        }
        .orders-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }
        .filter-group {
          display: flex;
          gap: 10px;
        }
        .filter-select {
          padding: 8px 12px;
          border: 1px solid #ccc;
          border-radius: 4px;
          font-size: 14px;
        }
        .orders-list {
          display: grid;
          gap: 15px;
        }
        .order-card {
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 16px;
          background: white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: box-shadow 0.2s;
        }
        .order-card:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .order-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        .order-id {
          display: flex;
          gap: 10px;
          align-items: center;
        }
        .priority {
          font-size: 12px;
          font-weight: bold;
          padding: 4px 8px;
          border-radius: 4px;
        }
        .priority-alta { background: #ffebee; color: #c62828; }
        .priority-media { background: #fff3e0; color: #e65100; }
        .priority-baja { background: #e8f5e9; color: #2e7d32; }
        .order-details {
          margin: 12px 0;
          font-size: 14px;
        }
        .detail-row {
          display: flex;
          gap: 10px;
          margin: 8px 0;
        }
        .detail-row .label {
          font-weight: 600;
          color: #666;
          min-width: 100px;
        }
        .detail-row .value {
          color: #333;
          flex: 1;
          word-break: break-word;
        }
        .order-actions {
          display: flex;
          gap: 10px;
          margin-top: 12px;
          flex-wrap: wrap;
        }
        .badge {
          display: inline-block;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
        }
        .badge-pending { background: #e0e0e0; color: #666; }
        .badge-assigned { background: #e3f2fd; color: #1976d2; }
        .badge-in-progress { background: #fff3e0; color: #f57c00; }
        .badge-completed { background: #e8f5e9; color: #388e3c; }
        .badge-cancelled { background: #ffebee; color: #d32f2f; }
        .badge-default { background: #f5f5f5; color: #666; }
        .error-alert {
          padding: 12px 16px;
          background: #ffebee;
          color: #c62828;
          border-radius: 4px;
          margin-bottom: 16px;
        }
        .empty-state {
          text-align: center;
          padding: 40px 20px;
          color: #999;
        }
        .loading {
          text-align: center;
          padding: 40px;
          color: #666;
        }
        .btn-primary, .btn-success {
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
          font-size: 14px;
          transition: all 0.2s;
        }
        .btn-primary {
          background: #1976d2;
          color: white;
        }
        .btn-primary:hover {
          background: #1565c0;
        }
        .btn-success {
          background: #388e3c;
          color: white;
        }
        .btn-success:hover {
          background: #2e7d32;
        }
        .text-muted {
          color: #999;
          font-size: 14px;
        }
      `}</style>
    </div>
  );
};
