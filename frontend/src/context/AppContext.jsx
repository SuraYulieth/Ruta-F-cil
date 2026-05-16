import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../services/api';

const AppContext = createContext();

export const useAppContext = () => useContext(AppContext);

export const AppProvider = ({ children }) => {
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [driverProfiles, setDriverProfiles] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [usersData, ordersData, warehousesData, driverProfilesData] = await Promise.all([
        api.getUsers(),
        api.getOrders(),
        api.getWarehouses(),
        api.getDrivers(),
      ]);
      setUsers(usersData);
      setOrders(ordersData);
      setWarehouses(warehousesData);
      setDriverProfiles(driverProfilesData);
    } catch (error) {
      console.error('Error al cargar datos del backend:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    try {
      setLoading(true);
      const data = await api.refreshImportedData();
      setUsers(data.users);
      setOrders(data.orders);
      setWarehouses(data.warehouses);
      setDriverProfiles(data.drivers);
      return data;
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
      throw error;
    }
  };

  const addUser = async (userData) => {
    try {
      const createdUser = await api.createUser(userData);
      await fetchData();
      return createdUser;
    } catch (error) {
      console.error('Error al agregar usuario:', error);
      throw error;
    }
  };

  const addWarehouse = async (warehouseData) => {
    const createdWarehouse = await api.createWarehouse(warehouseData);
    await fetchData();
    return createdWarehouse;
  };

  const addDriverProfile = async (driverData) => {
    const createdDriver = await api.createDriverProfile(driverData);
    await fetchData();
    return createdDriver;
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
  const importExcelData = async (file) => {
    const result = await api.importExcel(file);
    await refreshData();
    return result;
  };
  const assignOrder = async (orderId, driverId) => {
    try {
      const result = await api.assignOrderManually(orderId, driverId);

      setOrders((prev) => (
        prev.map((order) => (
          Number(order.id) === Number(orderId)
            ? {
                ...order,
                estado: 'Asignado',
                status: 'Asignado',
                driverId: Number(driverId),
              }
            : order
        ))
      ));

      await refreshData();
      return result;
    } catch (error) {
      console.error('Error al asignar pedido:', error);
      throw error;
    }
  };
  const getPendingOrders = async () => api.getPendingOrders();
  const getRoute = async (routeId) => api.getRoute(routeId);
  const getRouteEvidence = async (routeId) => api.getRouteEvidence(routeId);
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
      warehouses,
      driverProfiles,
      currentUser,
      loading,
      login,
      logout,
      addOrder,
      addUser,
      addWarehouse,
      addDriverProfile,
      getDrivers,
      updateOrderStatus,
      updateDriverStatus,
      assignOrders,
      optimizeRoute,
      assignOrder,
      importExcelData,
      getPendingOrders,
      getRoute,
      getRouteEvidence,
      assignOptimizedRoute,
      updateRouteStatus,
      refreshData,
    }}>
      {children}
    </AppContext.Provider>
  );
};
