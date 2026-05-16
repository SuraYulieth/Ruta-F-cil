import { useAppContext } from '../../context/AppContext';

export const DriverDashboard = () => {
  const { currentUser, orders, updateOrderStatus, updateDriverStatus } = useAppContext();

  // Filtrar las órdenes asignadas a este repartidor
  const myOrders = orders.filter(o => o.driverId === currentUser.id);

  const handleCompleteOrder = async (orderId) => {
    // 1. Marcar la orden como "Entregado"
    await updateOrderStatus(orderId, 'Entregado');
    // 2. Marcar al repartidor como "Disponible" de nuevo
    await updateDriverStatus(currentUser.id, 'Disponible');
  };

  const handleStartRoute = async (orderId) => {
    await updateOrderStatus(orderId, 'En ruta');
  };

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Mi Panel de Rutas</h1>
        <p>Hola, {currentUser.name}. Revisa tus rutas asignadas.</p>
      </header>

      <section className="panel mt-4">
        <h2>
          🛵 Rutas Pendientes <span className="count">{myOrders.filter(o => o.status !== 'Entregado').length}</span>
        </h2>
        
        {myOrders.length === 0 ? (
          <div className="empty-state">No tienes rutas asignadas en este momento.</div>
        ) : (
          <div className="list-container mt-4">
            {myOrders.map(order => (
              <div key={order.id} className={`card ${order.status === 'Entregado' ? 'opacity-50' : ''}`}>
                <div className="card-info">
                  <h3>{order.customer}</h3>
                  <p>📍 {order.destination}</p>
                </div>
                
                <div className="driver-actions">
                  <div className={`badge ${order.status.toLowerCase().replace(' ', '-')}`}>
                    {order.status}
                  </div>
                  
                  {order.status === 'Asignado' && (
                    <button 
                      className="btn-secondary"
                      onClick={() => handleStartRoute(order.id)}
                    >
                      Empezar Ruta
                    </button>
                  )}
                  
                  {order.status === 'En ruta' && (
                    <button 
                      className="btn-success"
                      onClick={() => handleCompleteOrder(order.id)}
                    >
                      ✅ Entregado
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
