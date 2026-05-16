const RAW_API_BASE_URL = (
  import.meta.env.VITE_API_URL
  || import.meta.env.VITE_API_BASE_URL
  || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

const API_BASE_URL = RAW_API_BASE_URL.endsWith('/api')
  ? RAW_API_BASE_URL
  : `${RAW_API_BASE_URL}/api`;

const apiPath = (path) => `${API_BASE_URL}${path}`;

const jsonHeaders = { 'Content-Type': 'application/json' };

// ============ TOKEN MANAGEMENT ============
export const tokenService = {
  setToken: (token) => {
    if (token) {
      localStorage.setItem('auth_token', token);
    }
  },
  
  getToken: () => localStorage.getItem('auth_token'),
  
  clearToken: () => {
    localStorage.removeItem('auth_token');
  },
  
  hasToken: () => !!localStorage.getItem('auth_token'),
};

const getAuthHeaders = () => {
  const token = tokenService.getToken();
  const headers = { ...jsonHeaders };
  
  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }
  
  return headers;
};

const getErrorMessage = (payload) => {
  if (!payload) return null;
  if (typeof payload === 'string') return payload;
  if (payload.error) return payload.error;
  if (payload.detail) return payload.detail;
  if (typeof payload === 'object') {
    const [field, value] = Object.entries(payload)[0] || [];
    const message = Array.isArray(value) ? value[0] : value;
    if (typeof message === 'string') {
      return field ? `${field}: ${message}` : message;
    }
    if (message && typeof message === 'object') {
      return getErrorMessage(message);
    }
  }
  return null;
};

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = isFormData ? getAuthHeaders() : { ...getAuthHeaders() };
  
  // No override Content-Type para FormData (el navegador lo hace automáticamente)
  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  
  const response = await fetch(apiPath(path), {
    headers,
    ...options,
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(getErrorMessage(payload) || 'Error al comunicarse con el servidor');
  }
  return payload;
}

export const api = {
  getUsers: () => request('/users/'),
  getOrders: () => request('/pedidos/'),
  getWarehouses: () => request('/aliados/'),
  getDrivers: () => request('/repartidores/'),
  getDriverDiagnostics: () => request('/repartidores/diagnostics/'),
  
  // ============ DRIVER ENDPOINTS (Token Auth Required) ============
  getDriverProfile: () => request('/drivers/me/'),
  toggleDriverAvailability: (disponible) => request('/drivers/me/toggle-availability/', {
    method: 'POST',
    body: JSON.stringify({ disponible }),
  }),
  getDriverOrders: (estado) => request(`/drivers/me/orders/${estado ? `?estado=${encodeURIComponent(estado)}` : ''}`, {
    method: 'GET',
  }),
  getDriverRoutes: (estado_ruta) => request(`/drivers/me/routes/${estado_ruta ? `?estado_ruta=${encodeURIComponent(estado_ruta)}` : ''}`, {
    method: 'GET',
  }),
  updateDriverLocation: (latitud, longitud) => request('/drivers/me/location/', {
    method: 'POST',
    body: JSON.stringify({ latitud, longitud }),
  }),
  startDriverOrder: (orderId) => request(`/drivers/me/orders/${orderId}/start/`, {
    method: 'POST',
  }),
  deliverDriverOrder: (orderId, comentarios) => request(`/drivers/me/orders/${orderId}/deliver/`, {
    method: 'POST',
    body: JSON.stringify({ comentarios }),
  }),
  completeDriverOrder: (orderId) => request(`/drivers/me/orders/${orderId}/complete/`, {
    method: 'POST',
  }),
  // Compat aliases used by existing components
  getMyDriverInfo: () => api.getDriverProfile(),
  getMyOrders: (estado) => api.getDriverOrders(estado),
  getMyRoutes: (estado_ruta) => api.getDriverRoutes(estado_ruta),
  updateMyLocation: (latitud, longitud) => api.updateDriverLocation(latitud, longitud),
  startOrder: (orderId) => api.startDriverOrder(orderId),
  deliverOrder: (orderId, comentarios) => api.deliverDriverOrder(orderId, comentarios),
  completeOrder: (orderId) => api.completeDriverOrder(orderId),
  refreshImportedData: () => Promise.all([
    api.getUsers(),
    api.getOrders(),
    api.getWarehouses(),
    api.getDrivers(),
  ]).then(([users, orders, warehouses, drivers]) => ({ users, orders, warehouses, drivers })),
  importExcel: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('/import-excel/', {
      method: 'POST',
      body: formData,
    });
  },
  getPendingOrders: () => request('/pedidos/').then((orders) => (
    orders.filter((order) => String(order.estado || order.status || '').toLowerCase() === 'pendiente')
  )),
  login: (username, password) => request('/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }),
  createOrder: (orderData) => request('/pedidos/', {
    method: 'POST',
    body: JSON.stringify(orderData),
  }),
  createUser: (userData) => request('/users/', {
    method: 'POST',
    body: JSON.stringify(userData),
  }),
  createWarehouse: (warehouseData) => request('/aliados/', {
    method: 'POST',
    body: JSON.stringify(warehouseData),
  }),
  createDriverProfile: (driverData) => request('/repartidores/', {
    method: 'POST',
    body: JSON.stringify(driverData),
  }),
  updateOrder: (orderId, data) => request(`/pedidos/${orderId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  updateUser: (userId, data) => request(`/users/${userId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  autoAssignOrders: () => request('/pedidos/asignar_automatico/', {
    method: 'POST',
  }),
  assignOrderManually: (orderId, driverId) => request(`/pedidos/${orderId}/assign/`, {
    method: 'POST',
    body: JSON.stringify({ repartidor_id: driverId }),
  }),
  optimizeRoute: (payload) => {
    const normalizedPayload = {
      modo: payload.modo,
      repartidor_id: payload.repartidor_id,
      latitud_inicial: payload.latitud_inicial ?? payload.latitud_inicio,
      longitud_inicial: payload.longitud_inicial ?? payload.longitud_inicio,
      pedidos_candidatos: payload.pedidos_candidatos,
      capacidad_maxima: payload.capacidad_maxima ?? payload.capacidad_maxima_kg,
      max_duration_mins: payload.max_duration_mins,
      max_area_km2: payload.max_area_km2,
      max_distance_km: payload.max_distance_km,
      reglas_negocio: payload.reglas_negocio,
    };

    return request('/routes/optimize/', {
      method: 'POST',
      body: JSON.stringify(normalizedPayload),
    });
  },
  getRoute: (routeId) => request(`/routes/${routeId}/`),
  getRouteEvidence: (routeId) => request(`/routes/${routeId}/evidence/`),
  assignRoute: (routeId) => request(`/routes/${routeId}/assign/`, {
    method: 'POST',
  }),
  updateRouteStatus: (routeId, status) => request(`/routes/${routeId}/status/`, {
    method: 'PATCH',
    body: JSON.stringify({ estado_ruta: status }),
  }),
};
