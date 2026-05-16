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

async function request(path, options = {}) {
  const response = await fetch(apiPath(path), {
    headers: jsonHeaders,
    ...options,
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.error || 'Error al comunicarse con el servidor');
  }
  return payload;
}

export const api = {
  getUsers: () => request('/users/'),
  getOrders: () => request('/pedidos/'),
  getPendingOrders: () => request('/pedidos/').then((orders) => (
    orders.filter((order) => order.status === 'Pendiente' || order.estado === 'Pendiente')
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
  optimizeRoute: (payload) => {
    const normalizedPayload = {
      repartidor_id: payload.repartidor_id,
      latitud_inicial: payload.latitud_inicial ?? payload.latitud_inicio,
      longitud_inicial: payload.longitud_inicial ?? payload.longitud_inicio,
      pedidos_candidatos: payload.pedidos_candidatos,
      capacidad_maxima: payload.capacidad_maxima ?? payload.capacidad_maxima_kg,
      reglas_negocio: payload.reglas_negocio,
    };

    return request('/routes/optimize/', {
      method: 'POST',
      body: JSON.stringify(normalizedPayload),
    });
  },
  getRoute: (routeId) => request(`/routes/${routeId}/`),
  assignRoute: (routeId) => request(`/routes/${routeId}/assign/`, {
    method: 'POST',
  }),
  updateRouteStatus: (routeId, status) => request(`/routes/${routeId}/status/`, {
    method: 'PATCH',
    body: JSON.stringify({ estado_ruta: status }),
  }),
};
