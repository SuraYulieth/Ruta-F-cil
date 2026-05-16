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

  const isAvailable = !!driverProfile?.disponible;
  const displayName = driverProfile?.nombre
    || currentUser?.name
    || currentUser?.nombre
    || currentUser?.username
    || 'Repartidor';

  const summary = useMemo(() => ({
    total: driverOrders.length,
    assigned: driverOrders.filter((item) => item.estado === 'Asignado').length,
    inProgress: driverOrders.filter((item) => item.estado === 'En ruta').length,
    delivered: driverOrders.filter((item) => item.estado === 'Entregado').length,
    activeRoutes: driverRoutes.filter((route) => ['asignada', 'en_ruta'].includes(route.estado_ruta)).length,
  }), [driverOrders, driverRoutes]);

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

  if (driverDashboardError?.includes('perfil')) {
    return (
      <div className="dashboard-content driver-dashboard">
        <section className="driver-shell-card driver-error-card">
          <span className="driver-kicker">Perfil requerido</span>
          <h1>Este usuario no tiene perfil de repartidor asociado.</h1>
          <p>Solicita al administrador crear el perfil de repartidor antes de usar este panel.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="dashboard-content driver-dashboard">
      <header className="driver-hero">
        <div>
          <span className="driver-kicker">Ruta Facil Driver</span>
          <h1>Hola, {displayName}</h1>
          <p>Gestiona tu disponibilidad, entregas activas y rutas asignadas.</p>
        </div>
        <div className={`driver-live-pill ${isAvailable ? 'is-online' : 'is-offline'}`}>
          <span />
          {isAvailable ? 'Online' : 'Offline'}
        </div>
      </header>

      {driverDashboardLoading && (
        <section className="driver-skeleton-grid">
          <div />
          <div />
          <div />
        </section>
      )}

      {(driverDashboardError || actionError) && (
        <div className="driver-toast driver-toast-error">
          {driverDashboardError || actionError}
        </div>
      )}

      {actionSuccess && (
        <div className="driver-toast driver-toast-success">
          {actionSuccess}
        </div>
      )}

      <section className={`driver-availability-card ${isAvailable ? 'available' : 'unavailable'}`}>
        <div className="availability-glow" />
        <div className="availability-main">
          <div className="availability-icon" aria-hidden="true">
            {isAvailable ? 'ON' : 'OFF'}
          </div>
          <div>
            <span className="driver-kicker">Estado del repartidor</span>
            <h2>{isAvailable ? 'DISPONIBLE' : 'NO DISPONIBLE'}</h2>
            <p>
              {isAvailable
                ? 'Listo para recibir asignaciones.'
                : 'No puedes recibir pedidos en este momento.'}
            </p>
          </div>
        </div>

        <button
          className={`availability-action ${isAvailable ? 'danger' : 'success'}`}
          disabled={actionLoading === 'toggle' || !driverProfile}
          onClick={() => runAction('toggle', toggleAvailability)}
        >
          {actionLoading === 'toggle'
            ? 'Procesando...'
            : isAvailable
              ? 'Deshabilitarme'
              : 'Activarme'}
        </button>
      </section>

      {!isAvailable && (
        <section className="driver-lock-alert">
          <strong>No puedes recibir pedidos en este momento.</strong>
          <span>Para volver a recibir asignaciones debes activarte nuevamente.</span>
        </section>
      )}

      <section className="driver-stat-grid">
        <article className="driver-stat-card">
          <span>Pedidos asignados</span>
          <strong>{summary.assigned}</strong>
          <small>Listos para iniciar</small>
        </article>
        <article className="driver-stat-card">
          <span>Pedidos en curso</span>
          <strong>{summary.inProgress}</strong>
          <small>Actualmente en ruta</small>
        </article>
        <article className="driver-stat-card">
          <span>Entregados hoy</span>
          <strong>{summary.delivered}</strong>
          <small>Completados</small>
        </article>
        <article className="driver-stat-card">
          <span>Rutas activas</span>
          <strong>{summary.activeRoutes}</strong>
          <small>Asignadas o en ruta</small>
        </article>
      </section>

      <main className="driver-work-grid">
        <section className="driver-panel">
          <div className="panel-title-row">
            <h2>Pedidos asignados</h2>
            <span className="count">{summary.total}</span>
          </div>

          {driverOrders.length === 0 ? (
            <div className="driver-empty-state">
              <strong>Sin pedidos asignados</strong>
              <p>Cuando recibas una asignacion aparecera en esta lista.</p>
            </div>
          ) : (
            <div className="driver-order-list">
              {driverOrders.map((order) => (
                <article className="driver-order-card" key={order.id}>
                  <div>
                    <div className="driver-order-head">
                      <strong>Pedido #{order.id}</strong>
                      <span>{order.estado}</span>
                    </div>
                    <p><strong>Cliente:</strong> {order.cliente_nombre || 'N/A'}</p>
                    <p><strong>Direccion:</strong> {order.direccion || 'N/A'}</p>
                  </div>
                  <div className="driver-order-actions">
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
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="driver-panel">
          <div className="panel-title-row">
            <h2>Ruta actual</h2>
          </div>
          {!currentRoute ? (
            <div className="driver-empty-state">
              <strong>No tienes ruta activa</strong>
              <p>Las rutas asignadas apareceran aqui con sus paradas.</p>
            </div>
          ) : (
            <div className="driver-route-card">
              <span>Ruta #{currentRoute.id}</span>
              <strong>{currentRoute.estado_ruta || 'Sin estado'}</strong>
              <p>Paradas: {currentRoute.total_paradas || currentRoute.paradas?.length || 0}</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};
