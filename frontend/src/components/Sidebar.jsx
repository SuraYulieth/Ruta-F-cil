import { NavLink, useNavigate } from 'react-router-dom';
import { useAppContext } from '../context/AppContext';

export const Sidebar = () => {
  const { currentUser, logout } = useAppContext();
  const navigate = useNavigate();
  const userDisplayName = currentUser?.name
    || currentUser?.nombre
    || currentUser?.username
    || currentUser?.email
    || 'Usuario';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Ruta Fácil</h2>
        <span className="role-badge">{currentUser?.role === 'admin' ? '👑 Admin' : '🛵 Repartidor'}</span>
      </div>

      <nav className="sidebar-nav">
        {currentUser?.role === 'admin' && (
          <>
            <NavLink to="/admin/dashboard" className={({isActive}) => isActive ? 'nav-item active' : 'nav-item'}>
              📊 Dashboard
            </NavLink>
            <NavLink to="/admin/routes" className={({isActive}) => isActive ? 'nav-item active' : 'nav-item'}>
              🗺️ Crear Ruta
            </NavLink>
            <NavLink to="/admin/users" className={({isActive}) => isActive ? 'nav-item active' : 'nav-item'}>
              👥 Gestión Usuarios
            </NavLink>
          </>
        )}
        
        {currentUser?.role === 'driver' && (
          <>
            <NavLink to="/driver/dashboard" className={({isActive}) => isActive ? 'nav-item active' : 'nav-item'}>
              🛵 Resumen
            </NavLink>
            <NavLink to="/driver/orders" className={({isActive}) => isActive ? 'nav-item active' : 'nav-item'}>
              📦 Pedidos
            </NavLink>
            <NavLink to="/driver/map" className={({isActive}) => isActive ? 'nav-item active' : 'nav-item'}>
              🗺️ Mapa
            </NavLink>
            <NavLink to="/driver/availability" className={({isActive}) => isActive ? 'nav-item active' : 'nav-item'}>
              🚦 Disponibilidad
            </NavLink>
            <NavLink to="/driver/stats" className={({isActive}) => isActive ? 'nav-item active' : 'nav-item'}>
              📊 Estadísticas
            </NavLink>
          </>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="user-info">
          <p className="user-name">{userDisplayName}</p>
        </div>
        <button className="btn-logout" onClick={handleLogout}>
          🚪 Salir
        </button>
      </div>
    </aside>
  );
};
