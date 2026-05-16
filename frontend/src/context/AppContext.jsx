import { createContext, useState, useContext, useEffect } from 'react';

const AppContext = createContext();

export const useAppContext = () => useContext(AppContext);

const API_BASE_URL = 'http://localhost:8000/api';

export const AppProvider = ({ children }) => {
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Cargar datos iniciales desde el Backend
  const fetchData = async () => {
    try {
      setLoading(true);
      const [usersRes, ordersRes] = await Promise.all([
        fetch(`${API_BASE_URL}/users/`),
        fetch(`${API_BASE_URL}/pedidos/`)
      ]);
      
      if (usersRes.ok && ordersRes.ok) {
        const usersData = await usersRes.json();
        const ordersData = await ordersRes.json();
        setUsers(usersData);
        setOrders(ordersData);
      }
    } catch (error) {
      console.error("Error al cargar datos del backend:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const login = async (username, password) => {
    try {
      const response = await fetch(`${API_BASE_URL}/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (response.ok) {
        const userData = await response.json();
        setCurrentUser(userData);
        return true;
      }
    } catch (error) {
      console.error("Error en el login:", error);
    }
    return false;
  };

  const logout = () => {
    setCurrentUser(null);
  };

  const addOrder = async (orderData) => {
    try {
      const response = await fetch(`${API_BASE_URL}/pedidos/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
      });

      if (response.ok) {
        await fetchData(); // Recargar datos para asegurar sincronización
      }
    } catch (error) {
      console.error("Error al agregar pedido:", error);
    }
  };

  const addUser = async (userData) => {
    try {
      const response = await fetch(`${API_BASE_URL}/users/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });

      if (response.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error("Error al agregar usuario:", error);
    }
  };

  const getDrivers = () => users.filter(u => u.role === 'driver');

  const updateOrderStatus = async (orderId, status) => {
    try {
      const response = await fetch(`${API_BASE_URL}/pedidos/${orderId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ estado: status })
      });

      if (response.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error("Error al actualizar pedido:", error);
    }
  };

  const updateDriverStatus = async (driverId, status) => {
    try {
      const response = await fetch(`${API_BASE_URL}/users/${driverId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ estado: status })
      });

      if (response.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error("Error al actualizar repartidor:", error);
    }
  };

  const assignOrders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/pedidos/asignar_automatico/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        await fetchData();
        return true;
      }
    } catch (error) {
      console.error("Error al asignar pedidos:", error);
    }
    return false;
  };

  return (
    <AppContext.Provider value={{
      users,
      orders,
      currentUser,
      loading,
      login,
      logout,
      addOrder,
      addUser,
      getDrivers,
      updateOrderStatus,
      updateDriverStatus,
      assignOrders
    }}>
      {children}
    </AppContext.Provider>
  );
};
