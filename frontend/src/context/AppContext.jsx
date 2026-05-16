import { createContext, useContext, useEffect, useState } from 'react';
import { api, tokenService } from '../services/api';

const AppContext = createContext();

const sessionService = {
  setUser: (user) => localStorage.setItem('auth_user', JSON.stringify(user)),
  getUser: () => {
    const raw = localStorage.getItem('auth_user');
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },
  clearUser: () => localStorage.removeItem('auth_user'),
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAppContext = () => useContext(AppContext);

export const AppProvider = ({ children }) => {
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [driverProfiles, setDriverProfiles] = useState([]);
  const [currentUser, setCurrentUser] = useState(() => sessionService.getUser());
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(() => tokenService.getToken());
  const [driverProfile, setDriverProfile] = useState(null);
  const [driverOrders, setDriverOrders] = useState([]);
  const [driverRoutes, setDriverRoutes] = useState([]);
  const [driverDashboardLoading, setDriverDashboardLoading] = useState(false);
  const [driverDashboardError, setDriverDashboardError] = useState('');

  const normalizeList = (value) => {
    if (Array.isArray(value)) return value;
    if (Array.isArray(value?.results)) return value.results;
    return [];
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const [usersData, ordersData, warehousesData, driverProfilesData] = await Promise.all([
        api.getUsers(),
        api.getOrders(),
        api.getWarehouses(),
        api.getDrivers(),
      ]);
      setUsers(normalizeList(usersData));
      setOrders(normalizeList(ordersData));
      setWarehouses(normalizeList(warehousesData));
      setDriverProfiles(normalizeList(driverProfilesData));
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
      setUsers(normalizeList(data.users));
      setOrders(normalizeList(data.orders));
      setWarehouses(normalizeList(data.warehouses));
      setDriverProfiles(normalizeList(data.drivers));
      return data;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
  }, []);

  useEffect(() => {
    if (!token || currentUser?.role !== 'driver') return;
    loadDriverDashboard().catch(() => {
      // El error ya se gestiona en estado de contexto para mostrar en UI.
    });
  }, [token, currentUser?.role]);

  const login = async (username, password) => {
    try {
      const userData = await api.login(username, password);
      
      // Guardar token si viene en la respuesta
      if (userData.token) {
        tokenService.setToken(userData.token);
        setToken(userData.token);
      }
      
      setCurrentUser(userData);
      sessionService.setUser(userData);
      if (userData.role === 'driver') {
        await loadDriverDashboard();
      }
      return true;
    } catch (error) {
      console.error('Error en el login:', error);
      return false;
    }
  };

  const logout = () => {
    setCurrentUser(null);
    setToken(null);
    tokenService.clearToken();
    sessionService.clearUser();
    setDriverProfile(null);
    setDriverOrders([]);
    setDriverRoutes([]);
    setDriverDashboardError('');
  };

  const loadDriverDashboard = async () => {
    try {
      setDriverDashboardLoading(true);
      setDriverDashboardError('');
      const [profileData, ordersData, routesData] = await Promise.all([
        api.getDriverProfile(),
        api.getDriverOrders(),
        api.getDriverRoutes(),
      ]);
      setDriverProfile(profileData || null);
      setDriverOrders(ordersData?.pedidos || []);
      setDriverRoutes(routesData?.rutas || []);
      return { profile: profileData, orders: ordersData?.pedidos || [], routes: routesData?.rutas || [] };
    } catch (error) {
      const message = error?.message || 'No se pudo cargar el panel del repartidor.';
      setDriverDashboardError(message);
      setDriverProfile(null);
      setDriverOrders([]);
      setDriverRoutes([]);
      throw error;
    } finally {
      setDriverDashboardLoading(false);
    }
  };

  const toggleAvailability = async () => {
    const previousProfile = driverProfile;
    const nextState = !driverProfile?.disponible;

    // Optimistic update para reflejar inmediatamente el cambio en UI
    if (driverProfile) {
      setDriverProfile({
        ...driverProfile,
        disponible: nextState,
        estado: nextState ? 'Disponible' : 'No disponible',
      });
    }

    try {
      const response = await api.toggleDriverAvailability(nextState);
      const available = typeof response?.available === 'boolean' ? response.available : response?.disponible;
      const serverProfile = response?.repartidor || null;

      if (serverProfile) {
        setDriverProfile(serverProfile);
      } else if (typeof available === 'boolean' && driverProfile) {
        setDriverProfile({
          ...driverProfile,
          disponible: available,
          estado: available ? 'Disponible' : 'No disponible',
        });
      }

      return {
        ...response,
        available,
        message: response?.message || response?.mensaje || 'Disponibilidad actualizada correctamente.',
      };
    } catch (error) {
      // Rollback en caso de falla
      setDriverProfile(previousProfile);
      throw error;
    }
  };

  const updateDriverLocation = async (latitud, longitud) => {
    const response = await api.updateDriverLocation(latitud, longitud);
    if (response?.repartidor) {
      setDriverProfile(response.repartidor);
    }
    return response;
  };

  const startOrder = async (orderId) => {
    const response = await api.startDriverOrder(orderId);
    await loadDriverDashboard();
    return response;
  };

  const deliverOrder = async (orderId, comentarios = '') => {
    const response = await api.deliverDriverOrder(orderId, comentarios);
    await loadDriverDashboard();
    return response;
  };

  const completeOrder = async (orderId) => {
    const response = await api.completeDriverOrder(orderId);
    await loadDriverDashboard();
    return response;
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

  const getDrivers = () => normalizeList(users).filter((user) => user.role === 'driver');

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
      token,
      loading,
      driverProfile,
      driverOrders,
      driverRoutes,
      driverDashboardLoading,
      driverDashboardError,
      login,
      logout,
      loadDriverDashboard,
      toggleAvailability,
      updateDriverLocation,
      startOrder,
      deliverOrder,
      completeOrder,
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
