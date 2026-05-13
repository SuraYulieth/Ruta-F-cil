import { useState } from 'react';
import './App.css';

// Mock Data
const initialOrders = [
  { id: 'ORD-1023', desc: 'Paquete pequeño - Electrónicos', status: 'pending', customer: 'David Restrepo', location: 'El Poblado' },
  { id: 'ORD-1024', desc: 'Caja mediana - Ropa', status: 'pending', customer: 'Sura Rueda', location: 'Laureles' },
  { id: 'ORD-1025', desc: 'Documentos urgentes', status: 'assigned', customer: 'Karen Rodriguez', location: 'Envigado', driver: 'Carlos M.' }
];

const nearbyDrivers = [
  { id: 'DRV-01', name: 'Carlos M.', status: 'busy', distance: '1.2 km' },
  { id: 'DRV-02', name: 'Ana G.', status: 'available', distance: '0.8 km' },
  { id: 'DRV-03', name: 'Luis P.', status: 'available', distance: '3.5 km' },
];

function App() {
  const [orders, setOrders] = useState(initialOrders);
  const [isAssigning, setIsAssigning] = useState(false);

  const handleAssignOrders = () => {
    setIsAssigning(true);
    // Simulate AI / Algorithm calculating nearest store and driver
    setTimeout(() => {
      setOrders(prev => prev.map(o => {
        if (o.status === 'pending') {
          return { ...o, status: 'assigned', driver: 'Ana G.' };
        }
        return o;
      }));
      setIsAssigning(false);
    }, 1500);
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo-icon">M</div>
          <div className="logo-text">MultiFast</div>
        </div>
        <nav className="nav-menu">
          <div className="nav-item active">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
            Dashboard
          </div>
          <div className="nav-item">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"></path><path d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"></path></svg>
            Rutas
          </div>
          <div className="nav-item">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
            Repartidores
          </div>
          <div className="nav-item">
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>
            Bodegas / Tiendas
          </div>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="header">
          <div>
            <h1>Centro de Asignación Ruta Fácil</h1>
            <p style={{ color: 'var(--text-muted)', marginTop: '4px' }}>Optimización logística y asignación inteligente.</p>
          </div>
          <div className="header-actions">
            <div className="user-profile">
              <div className="avatar">A</div>
              <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>Admin</span>
            </div>
          </div>
        </header>

        <div className="dashboard-grid">
          {/* Active Orders List */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Pedidos Pendientes y En Ruta</h2>
              <button 
                className="btn btn-primary" 
                onClick={handleAssignOrders}
                disabled={isAssigning}
              >
                {isAssigning ? 'Optimizando...' : 'Asignar a más cercano (IA)'}
              </button>
            </div>
            
            <div className="order-list">
              {orders.map((order, idx) => (
                <div key={order.id} className="order-item" style={{ animationDelay: `${idx * 0.1}s` }}>
                  <div className="order-info">
                    <span className="order-id">{order.id}</span>
                    <span className="order-desc">{order.desc}</span>
                    <div className="order-meta">
                      <span style={{ color: 'var(--text-muted)' }}>📍 {order.location}</span>
                      <span style={{ color: 'var(--text-muted)' }}>👤 {order.customer}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                    <span className={`badge ${order.status}`}>
                      {order.status === 'pending' ? 'Pendiente' : 'Asignado'}
                    </span>
                    {order.driver && (
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        Repartidor: <strong style={{ color: 'var(--text-main)' }}>{order.driver}</strong>
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Panel: Map & Drivers */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Map Simulator */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <div className="map-placeholder">
                <div className="map-grid"></div>
                <div className="map-text">Simulación GPS en Vivo</div>
                <div className="map-pin pin-store" title="Bodega Principal"></div>
                <div className="map-pin pin-driver" title="Repartidor (Ana G.)"></div>
                <div className="map-pin pin-customer" title="Destino Cliente"></div>
              </div>
            </div>

            {/* Drivers Nearby */}
            <div className="card">
              <div className="card-header" style={{ marginBottom: '1rem' }}>
                <h2 className="card-title">Repartidores Cercanos</h2>
              </div>
              <div className="order-list">
                {nearbyDrivers.map(driver => (
                  <div key={driver.id} className="order-item" style={{ padding: '12px' }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{driver.name}</div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                        Distancia: {driver.distance}
                      </div>
                    </div>
                    <span className={`badge ${driver.status === 'available' ? 'delivered' : 'pending'}`}>
                      {driver.status === 'available' ? 'Disponible' : 'En ruta'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
