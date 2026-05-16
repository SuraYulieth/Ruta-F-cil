import { useState } from 'react';
import { useAppContext } from '../../context/AppContext';

export const AdminDashboard = () => {
  const { orders, getDrivers, assignOrders } = useAppContext();
  const [isAssigning, setIsAssigning] = useState(false);
  
  const drivers = getDrivers();

  // Llamada al Algoritmo de Asignación en el Backend
  const handleAssignOrders = async () => {
    setIsAssigning(true);
    await assignOrders();
    setIsAssigning(false);
  };

  const pendingCount = orders.filter(o => o.status === 'Pendiente').length;
  const availableCount = drivers.filter(d => d.status === 'Disponible').length;

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Dashboard de Asignación</h1>
        <p>Visión general y optimización de rutas en tiempo real.</p>
      </header>

      <main className="main-grid">
        <section className="panel">
          <h2>
            📦 Pedidos Activos <span className="count">{orders.length}</span>
          </h2>
          <div className="list-container">
            {orders.map(order => (
              <div key={order.id} className="card">
                <div className="card-info">
                  <h3>{order.customer}</h3>
                  <p>📍 {order.destination}</p>
                  {order.driverId && (
                    <p>🛵 Repartidor ID: {order.driverId}</p>
                  )}
                </div>
                <div className={`badge ${order.status.toLowerCase().replace(' ', '-')}`}>
                  {order.status}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>
            🛵 Repartidores en Zona <span className="count">{drivers.length}</span>
          </h2>
          <div className="list-container">
            {drivers.map(driver => (
              <div key={driver.id} className="card">
                <div className="card-info">
                  <h3>{driver.name}</h3>
                  <p>🌍 {driver.location}</p>
                </div>
                <div className={`badge ${driver.status.toLowerCase()}`}>
                  {driver.status}
                </div>
              </div>
            ))}
          </div>

          <div className="actions">
            <button 
              className="btn-primary" 
              onClick={handleAssignOrders}
              disabled={isAssigning || pendingCount === 0 || availableCount === 0}
            >
              {isAssigning ? (
                <>
                  <div className="spinner"></div>
                  Procesando Rutas...
                </>
              ) : (
                '🚀 Asignar a más cercano'
              )}
            </button>
          </div>
        </section>
      </main>
    </div>
  );
};
