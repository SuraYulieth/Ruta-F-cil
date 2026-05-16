import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useAppContext } from './context/AppContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Sidebar } from './components/Sidebar';

// Pages
import { Login } from './pages/Login';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { CreateRoute } from './pages/admin/CreateRoute';
import { ManageUsers } from './pages/admin/ManageUsers';
import { DriverDashboard } from './pages/driver/DriverDashboard';

import './App.css';

// Layout global para rutas protegidas
const ProtectedLayout = ({ children }) => {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        {children}
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
      <Route path="/admin/*" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <ProtectedLayout>
            <Routes>
              <Route path="dashboard" element={<AdminDashboard />} />
              <Route path="routes" element={<CreateRoute />} />
              <Route path="users" element={<ManageUsers />} />
            </Routes>
          </ProtectedLayout>
        </ProtectedRoute>
      } />

      {/* Rutas de Repartidor */}
      <Route path="/driver/*" element={
        <ProtectedRoute allowedRoles={['driver']}>
          <ProtectedLayout>
            <Routes>
              <Route path="dashboard" element={<DriverDashboard />} />
            </Routes>
          </ProtectedLayout>
        </ProtectedRoute>
      } />
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
