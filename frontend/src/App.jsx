import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AppProvider, useAppContext } from './context/AppContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Sidebar } from './components/Sidebar';
import { ErrorBoundary } from './components/ErrorBoundary';

// Pages
import { Login } from './pages/Login';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { CreateRoute } from './pages/admin/CreateRoute';
import { ManageUsers } from './pages/admin/ManageUsers';
import { DriverDashboard } from './pages/driver/DriverDashboard';
import { DriverOrders } from './pages/driver/DriverOrders';
import { DriverMap } from './pages/driver/DriverMap';
import { DriverAvailability } from './pages/driver/DriverAvailability';
import { DriverStats } from './pages/driver/DriverStats';

import './App.css';

// Layout global para rutas protegidas
const ProtectedLayout = () => {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Outlet />
      </div>
    </div>
  );
};

// Componente principal de rutas
const AppRoutes = () => {
  const { currentUser } = useAppContext();

  return (
    <Routes>
      {/* Redirección Inicial */}
      <Route path="/" element={
        currentUser ? (
          <Navigate to={currentUser.role === 'admin' ? '/admin/dashboard' : '/driver/dashboard'} replace />
        ) : (
          <Navigate to="/login" replace />
        )
      } />

      <Route path="/login" element={<Login />} />

      {/* Rutas de Administrador */}
      <Route path="/admin" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <ProtectedLayout />
        </ProtectedRoute>
      }>
        <Route
          path="dashboard"
          element={(
            <ErrorBoundary fallbackMessage="No se pudo cargar el dashboard de administrador.">
              <AdminDashboard />
            </ErrorBoundary>
          )}
        />
        <Route path="routes" element={<CreateRoute />} />
        <Route path="users" element={<ManageUsers />} />
        <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
      </Route>

      {/* Rutas de Repartidor */}
      <Route path="/driver" element={
        <ProtectedRoute allowedRoles={['driver']}>
          <ProtectedLayout />
        </ProtectedRoute>
      }>
        <Route path="dashboard" element={<DriverDashboard />} />
        <Route path="orders" element={<DriverOrders />} />
        <Route path="map" element={<DriverMap />} />
        <Route path="availability" element={<DriverAvailability />} />
        <Route path="stats" element={<DriverStats />} />
        <Route path="*" element={<Navigate to="/driver/dashboard" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <AppProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AppProvider>
  );
}

export default App;
