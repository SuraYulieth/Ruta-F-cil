import { useEffect, useMemo, useState } from 'react';
import { useAppContext } from '../../context/AppContext';

export const DriverDashboard = () => {
  const {
    currentUser,
    token,
    driverProfile,
    driverOrders,
    driverRoutes,
    driverDashboardLoading,
    driverDashboardError,
    loadDriverDashboard,
    toggleAvailability,
    startOrder,
    deliverOrder,
    completeOrder,
  } = useAppContext();

  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const [actionLoading, setActionLoading] = useState('');

  useEffect(() => {
    if (!token) return;
    loadDriverDashboard().catch(() => {
      // El error queda en contexto para renderizarlo en pantalla.
    });
  }, [token]);

  const summary = useMemo(() => ({
    total: driverOrders.length,
    assigned: driverOrders.filter((item) => item.estado === 'Asignado').length,
    inProgress: driverOrders.filter((item) => item.estado === 'En ruta').length,
    delivered: driverOrders.filter((item) => item.estado === 'Entregado').length,
  }), [driverOrders]);

  const displayName = driverProfile?.nombre
    || currentUser?.name
    || currentUser?.nombre
    || currentUser?.username
    || 'Repartidor';

  const currentRoute = driverRoutes[0] || null;

  const runAction = async (label, callback) => {
    try {
      setActionError('');
      setActionSuccess('');
      setActionLoading(label);
      const response = await callback();
      if (label === 'toggle') {
        setActionSuccess(response?.message || response?.mensaje || 'Disponibilidad actualizada.');
      }
    } catch (error) {
      setActionError(error?.message || 'No se pudo ejecutar la accion.');
    } finally {
      setActionLoading('');
    }
  };

  if (!token) {
    return (
      <div className="dashboard-content">
        <div className="panel mt-4">
          <p>Tu sesion expiro. Inicia sesion nuevamente.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Panel del Repartidor</h1>
        <p>Hola, {displayName}.</p>
      </header>

      {driverDashboardLoading && (
        <section className="panel mt-4">
          <p>Cargando informacion del repartidor...</p>
        </section>
      )}

      {(driverDashboardError || actionError) && (
        <section className="panel mt-4" style={{ borderLeft: '4px solid #c62828' }}>
          <p style={{ color: '#c62828', margin: 0 }}>
            {driverDashboardError || actionError}
          </p>
          {driverDashboardError?.includes('perfil') && (
            <p style={{ marginTop: 8 }}>Este usuario no tiene perfil de repartidor asociado.</p>
          )}
        </section>
      )}

      {actionSuccess && (
        <section className="panel mt-4" style={{ borderLeft: '4px solid #2e7d32' }}>
          <p style={{ color: '#2e7d32', margin: 0 }}>{actionSuccess}</p>
        </section>
      )}

      <section className="panel mt-4">
        <h2>Estado del repartidor</h2>
        <div
          className="card"
          style={{
            marginTop: 12,
            border: `2px solid ${driverProfile?.disponible ? '#2e7d32' : '#7b1f1f'}`,
            background: driverProfile?.disponible ? '#e8f5e9' : '#ffebee',
            display: 'grid',
            gap: 10,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <strong style={{ fontSize: 16 }}>Estado del repartidor</strong>
            <span
              style={{
                padding: '6px 12px',
                borderRadius: 999,
                fontWeight: 700,
                color: '#fff',
                background: driverProfile?.disponible ? '#2e7d32' : '#616161',
              }}
            >
              {driverProfile?.disponible ? 'Disponible' : 'No disponible'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
            <span><strong>Repartidor:</strong> {displayName}</span>
            <button
              className="btn-secondary"
              style={{
                minWidth: 180,
                background: driverProfile?.disponible ? '#c62828' : '#2e7d32',
                color: '#fff',
                border: 'none',
              }}
              disabled={actionLoading === 'toggle'}
              onClick={() => runAction('toggle', toggleAvailability)}
            >
              {actionLoading === 'toggle'
                ? 'Procesando...'
                : driverProfile?.disponible
                  ? 'Deshabilitarme'
                  : 'Activarme'}
            </button>
          </div>
        </div>
      </section>

      <section className="panel mt-4">
        <h2>Resumen de pedidos</h2>
        <div className="list-container mt-4" style={{ display: 'grid', gap: 10 }}>
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between' }}><strong>Total</strong><span>{summary.total}</span></div>
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between' }}><strong>Asignados</strong><span>{summary.assigned}</span></div>
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between' }}><strong>En ruta</strong><span>{summary.inProgress}</span></div>
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between' }}><strong>Entregados</strong><span>{summary.delivered}</span></div>
        </div>
      </section>

      <section className="panel mt-4">
        <h2>Pedidos asignados</h2>
        {driverOrders.length === 0 ? (
          <p>No tienes pedidos asignados todavia.</p>
        ) : (
          <div className="list-container mt-4" style={{ display: 'grid', gap: 12 }}>
            {driverOrders.map((order) => (
              <div className="card" key={order.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <strong>Pedido #{order.id}</strong>
                  <span>{order.estado}</span>
                </div>
                <p style={{ marginTop: 8, marginBottom: 6 }}><strong>Cliente:</strong> {order.cliente_nombre || 'N/A'}</p>
                <p style={{ marginTop: 0, marginBottom: 10 }}><strong>Direccion:</strong> {order.direccion || 'N/A'}</p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button
                    className="btn-secondary"
                    disabled={actionLoading === `start-${order.id}` || order.estado !== 'Asignado'}
                    onClick={() => runAction(`start-${order.id}`, () => startOrder(order.id))}
                  >
                    Iniciar entrega
                  </button>
                  <button
                    className="btn-secondary"
                    disabled={actionLoading === `deliver-${order.id}` || order.estado !== 'En ruta'}
                    onClick={() => runAction(`deliver-${order.id}`, () => deliverOrder(order.id))}
                  >
                    Marcar entregado
                  </button>
                  <button
                    className="btn-secondary"
                    disabled={actionLoading === `complete-${order.id}` || order.estado === 'Entregado'}
                    onClick={() => runAction(`complete-${order.id}`, () => completeOrder(order.id))}
                  >
                    Completar pedido
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel mt-4">
        <h2>Ruta actual</h2>
        {!currentRoute ? (
          <p>No tienes ruta activa en este momento.</p>
        ) : (
          <div className="card">
            <p><strong>Ruta:</strong> #{currentRoute.id}</p>
            <p><strong>Estado:</strong> {currentRoute.estado_ruta || 'N/A'}</p>
            <p><strong>Paradas:</strong> {currentRoute.total_paradas || currentRoute.paradas?.length || 0}</p>
          </div>
        )}
      </section>

      <section className="panel mt-4">
        <h2>Mapa de entregas</h2>
        <div className="card" style={{ minHeight: 180, display: 'grid', placeItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <p style={{ margin: 0 }}>Mapa de entregas del repartidor</p>
            <small>Placeholder operativo. Puede reemplazarse por Google Maps o Leaflet.</small>
          </div>
        </div>
      </section>
    </div>
  );
};
