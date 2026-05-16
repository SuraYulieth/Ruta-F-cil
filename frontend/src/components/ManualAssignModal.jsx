import { useEffect, useState } from 'react';
import './ManualAssignModal.css';

const normalizeText = (value) => String(value || '').trim().toLowerCase();
const isDriverRole = (driver) => ['driver', 'repartidor'].includes(normalizeText(driver?.role));
const isAvailableStatus = (driver) => ['disponible', 'activo', 'active', 'available']
  .includes(normalizeText(driver?.status || driver?.estado));
const isAvailableForManualAssign = (driver) => (
  isDriverRole(driver) && driver?.disponible === true && isAvailableStatus(driver)
);
const getHiddenReason = (driver) => {
  if (!isDriverRole(driver)) return 'No aparece porque role no es driver/repartidor.';
  if (driver?.disponible !== true) return 'No aparece porque esta No disponible.';
  if (!isAvailableStatus(driver)) return 'No aparece porque su estado no es disponible/activo.';
  return '';
};

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

  const filteredDrivers = drivers.filter(isDriverRole);
  const availableDrivers = filteredDrivers.filter(isAvailableForManualAssign);
  const hiddenDrivers = filteredDrivers
    .filter((driver) => !isAvailableForManualAssign(driver))
    .map((driver) => ({
      id: driver.id,
      name: driver.name || driver.nombre || `Repartidor ${driver.id}`,
      reason: driver.motivo_visibilidad || getHiddenReason(driver),
    }));

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
            <p className="helper-message">
              La asignacion manual permite repartidores disponibles aunque no tengan coordenadas.
            </p>
            {availableDrivers.length === 0 && (
              <p className="warning-message mt-4">
                No hay repartidores disponibles. Los repartidores deshabilitados no pueden recibir pedidos.
              </p>
            )}
            {hiddenDrivers.length > 0 && (
              <div className="driver-diagnostics">
                <strong>Repartidores ocultos</strong>
                {hiddenDrivers.map((driver) => (
                  <p key={driver.id}>{driver.name}: {driver.reason}</p>
                ))}
              </div>
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
