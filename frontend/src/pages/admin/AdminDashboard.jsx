import { useState } from 'react';
import { PendingOrdersMap } from '../../components/PendingOrdersMap';
import { RouteOptimizerPanel } from '../../components/RouteOptimizerPanel';
import { useAppContext } from '../../context/AppContext';

export const AdminDashboard = () => {
  const { orders, getDrivers, assignOrders } = useAppContext();
  const [isAssigning, setIsAssigning] = useState(false);
  const [optimization, setOptimization] = useState(null);

  const drivers = getDrivers();
  const pendingCount = orders.filter((order) => order.status === 'Pendiente' || order.estado === 'Pendiente').length;
  const availableCount = drivers.filter((driver) => driver.status === 'Disponible').length;

  const handleAssignOrders = async () => {
    setIsAssigning(true);
    await assignOrders();
    setIsAssigning(false);
  };

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Dashboard de asignacion</h1>
        <p>Pedidos, repartidores y optimizacion multi-pedido en una sola vista.</p>
      </header>

      <main className="optimizer-grid">
        <PendingOrdersMap
          orders={orders}
          selectedOrderIds={optimization?.optimizer?.pedidos_seleccionados || []}
          routeGeometry={optimization?.optimizer?.geometria}
        />
        <RouteOptimizerPanel onOptimized={setOptimization} />
      </main>

      <main className="main-grid mt-4">
        <section className="panel">
          <h2>Pedidos activos <span className="count">{orders.length}</span></h2>
          <div className="list-container">
            {orders.map((order) => (
              <div key={order.id} className="card">
                <div className="card-info">
                  <h3>{order.customer}</h3>
                  <p>{order.destination}</p>
                  {order.driverId && <p>Repartidor ID: {order.driverId}</p>}
                </div>
                <div className={`badge ${(order.status || order.estado).toLowerCase().replace(' ', '-')}`}>
                  {order.status || order.estado}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Repartidores en zona <span className="count">{drivers.length}</span></h2>
          <div className="list-container">
            {drivers.map((driver) => (
              <div key={driver.id} className="card">
                <div className="card-info">
                  <h3>{driver.name}</h3>
                  <p>{driver.location}</p>
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
              {isAssigning ? 'Procesando...' : 'Asignacion simple heredada'}
            </button>
          </div>
        </section>
      </main>
    </div>
  );
};
