import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../services/api';

const AppContext = createContext();

export const useAppContext = () => useContext(AppContext);

export const AppProvider = ({ children }) => {
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [usersData, ordersData] = await Promise.all([
        api.getUsers(),
        api.getOrders(),
      ]);
      setUsers(usersData);
      setOrders(ordersData);
    } catch (error) {
      console.error('Error al cargar datos del backend:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const login = async (username, password) => {
    try {
      const userData = await api.login(username, password);
      setCurrentUser(userData);
      return true;
    } catch (error) {
      console.error('Error en el login:', error);
      return false;
    }
  };

  const logout = () => {
    setCurrentUser(null);
  };

  const addOrder = async (orderData) => {
    try {
      await api.createOrder(orderData);
      await fetchData();
    } catch (error) {
      console.error('Error al agregar pedido:', error);
    }
  };

  const addUser = async (userData) => {
    try {
      await api.createUser(userData);
      await fetchData();
    } catch (error) {
      console.error('Error al agregar usuario:', error);
    }
  };

  const getDrivers = () => users.filter((user) => user.role === 'driver');

  const updateOrderStatus = async (orderId, nextStatus) => {
    try {
      await api.updateOrder(orderId, { estado: nextStatus });
      await fetchData();
    } catch (error) {
      console.error('Error al actualizar pedido:', error);
    }
  };

  const updateDriverStatus = async (driverId, nextStatus) => {
    try {
      await api.updateUser(driverId, { estado: nextStatus });
      await fetchData();
    } catch (error) {
      console.error('Error al actualizar repartidor:', error);
    }
  };

  const assignOrders = async () => {
    try {
      await api.autoAssignOrders();
      await fetchData();
      return true;
    } catch (error) {
      console.error('Error al asignar pedidos:', error);
      return false;
    }
  };

  const optimizeRoute = async (payload) => api.optimizeRoute(payload);
  const getPendingOrders = async () => api.getPendingOrders();
  const getRoute = async (routeId) => api.getRoute(routeId);
  const updateRouteStatus = async (routeId, status) => api.updateRouteStatus(routeId, status);

  const assignOptimizedRoute = async (routeId) => {
    const route = await api.assignRoute(routeId);
    await fetchData();
    return route;
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
      assignOrders,
      optimizeRoute,
      getPendingOrders,
      getRoute,
      assignOptimizedRoute,
      updateRouteStatus,
      refreshData: fetchData,
    }}>
      {children}
    </AppContext.Provider>
  );
};
