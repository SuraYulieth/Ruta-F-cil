const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const jsonHeaders = { 'Content-Type': 'application/json' };

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
  optimizeRoute: (payload) => request('/routes/optimize/', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  assignRoute: (routeId) => request(`/routes/${routeId}/assign/`, {
    method: 'POST',
  }),
  updateRouteStatus: (routeId, estadoRuta) => request(`/routes/${routeId}/status/`, {
    method: 'PATCH',
    body: JSON.stringify({ estado_ruta: estadoRuta }),
  }),
};
