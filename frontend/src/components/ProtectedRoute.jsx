import { Navigate } from 'react-router-dom';
import { useAppContext } from '../context/AppContext';

export const ProtectedRoute = ({ children, allowedRoles }) => {
  const { currentUser, token } = useAppContext();

  // Si no hay token ni usuario, redirigir al login
  if (!token || !currentUser) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(currentUser.role)) {
    // Si no tiene el rol, mandarlo a su dashboard respectivo
    return <Navigate to={currentUser.role === 'admin' ? '/admin/dashboard' : '/driver/dashboard'} replace />;
  }

  return children;
};
