import { useEffect, useState } from 'react';
import './ManualAssignModal.css';

export const ManualAssignModal = ({
  isOpen,
  order,
  drivers,
  onAssign,
  onClose,
  isLoading = false,
  error = null,
}) => {
  const [selectedDriverId, setSelectedDriverId] = useState(null);

  useEffect(() => {
    if (!isOpen) {
      setSelectedDriverId(null);
    }
  }, [isOpen]);

  const handleAssign = async () => {
    if (!selectedDriverId) {
      alert('Selecciona un repartidor');
      return;
    }

    await onAssign(order.id, selectedDriverId);
  };

  const handleClose = () => {
    setSelectedDriverId(null);
    onClose();
  };

  if (!isOpen) return null;

  const filteredDrivers = drivers.filter((driver) => driver.role === 'driver');
  const availableDrivers = filteredDrivers.filter((driver) => (
    driver.disponible !== false
    && String(driver.status || driver.estado || '').toLowerCase() === 'disponible'
  ));

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Asignar Pedido Manualmente</h2>
          <button className="modal-close" onClick={handleClose}>×</button>
        </div>

        <div className="modal-body">
          {order && (
            <div className="order-info">
              <p><strong>Pedido:</strong> #{order.id}</p>
              <p><strong>Cliente:</strong> {order.customer || 'N/A'}</p>
              <p><strong>Dirección:</strong> {order.destination || 'N/A'}</p>
              <p><strong>Peso:</strong> {order.weightKg || 0} kg</p>
              <p><strong>Prioridad:</strong> {order.priority || 'normal'}</p>
            </div>
          )}

          <div className="driver-selector">
            <label htmlFor="driver-select">Selecciona un repartidor:</label>
            <select
              id="driver-select"
              value={selectedDriverId || ''}
              onChange={(e) => setSelectedDriverId(e.target.value ? Number(e.target.value) : null)}
              disabled={isLoading}
            >
              <option value="">-- Seleccionar --</option>
              {availableDrivers.map((driver) => (
                <option key={driver.id} value={driver.id}>
                  {driver.name || driver.nombre} ({driver.status || driver.estado})
                </option>
              ))}
            </select>
            {availableDrivers.length === 0 && (
              <p className="warning-message mt-4">
                No hay repartidores disponibles. Los repartidores deshabilitados no pueden recibir pedidos.
              </p>
            )}
          </div>

          {error && <div className="error-message">{error}</div>}
        </div>

        <div className="modal-footer">
          <button
            className="btn btn-cancel"
            onClick={handleClose}
            disabled={isLoading}
          >
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            onClick={handleAssign}
            disabled={isLoading || !selectedDriverId}
          >
            {isLoading ? 'Asignando...' : 'Confirmar Asignación'}
          </button>
        </div>
      </div>
    </div>
  );
};
