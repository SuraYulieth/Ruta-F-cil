import { useState } from 'react';
import { PendingOrdersMap } from '../../components/PendingOrdersMap';
import { RouteOptimizerPanel } from '../../components/RouteOptimizerPanel';
import { useAppContext } from '../../context/AppContext';
import { ManualAssignModal } from '../../components/ManualAssignModal';

const normalizeText = (value) => String(value || '').trim().toLowerCase();
const isAvailableDriver = (driver) => (
  driver?.disponible === true
  && ['disponible', 'activo', 'active', 'available'].includes(normalizeText(driver?.status || driver?.estado))
);
const getDriverCoordinates = (driver) => {
  const lat = Number(driver?.latitud_actual ?? driver?.latitud ?? driver?.latitude);
  const lng = Number(driver?.longitud_actual ?? driver?.longitud ?? driver?.longitude);
  return Number.isFinite(lat) && Number.isFinite(lng) ? { lat, lng } : null;
};

export const AdminDashboard = () => {
  const {
    orders,
    routes,
    warehouses,
    getDrivers,
    assignOrders,
    assignOrder,
    refreshData,
    importExcelData,
    loading,
  } = useAppContext();

  const safeOrders = Array.isArray(orders) ? orders : [];
  const safeRoutes = Array.isArray(routes) ? routes : [];
  const safeWarehouses = Array.isArray(warehouses) ? warehouses : [];

  const getOrderStatus = (order) => String(order?.status || order?.estado || 'Sin estado');
  const getOrderCustomer = (order) => order?.customer || order?.cliente_nombre || order?.cliente?.nombre || 'Cliente sin nombre';
  const getOrderDestination = (order) => order?.destination || order?.direccion || order?.cliente?.direccion || 'Direccion no disponible';
  const getOrderWeight = (order) => order?.weightKg ?? order?.peso_total_kg ?? 0;
  const getOrderPriority = (order) => order?.priority || order?.prioridad || 'normal';
  const getOrderDriverId = (order) => order?.driverId || order?.repartidor_info?.id || order?.repartidor || null;
  const getOrderDriverName = (order) => order?.repartidor_nombre || order?.repartidor_info?.name || order?.repartidor_info?.nombre || getOrderDriverId(order) || 'Sin repartidor';
  const getOrderRouteId = (order) => order?.ruta_id || order?.routeId || null;
  const getOrderStopOrder = (order) => order?.orden_entrega || order?.stopOrder || null;

  const [isAssigning, setIsAssigning] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [importMessage, setImportMessage] = useState('');
  const [importError, setImportError] = useState('');
  const [importSummary, setImportSummary] = useState(null);
  const [optimization, setOptimization] = useState(null);
  const [driverLocation, setDriverLocation] = useState({ lat: 4.7110, lng: -74.0721 });
  const [selectedOptimizerDriver, setSelectedOptimizerDriver] = useState(null);
  const [manualAssignModal, setManualAssignModal] = useState({ isOpen: false, order: null });
  const [assignmentLoading, setAssignmentLoading] = useState(false);
  const [assignmentError, setAssignmentError] = useState('');
  const [assignmentSuccess, setAssignmentSuccess] = useState('');

  const isPendingOrder = (order) => String(order.estado || order.status || '').toLowerCase() === 'pendiente';
  const isAssignedOrder = (order) => String(order.estado || order.status || '').toLowerCase() === 'asignado';
  const isActiveOrder = (order) => ['asignado', 'en ruta', 'en_ruta'].includes(String(order.estado || order.status || '').toLowerCase());

  const drivers = Array.isArray(getDrivers?.()) ? getDrivers() : [];
  const pendingCount = safeOrders.filter(isPendingOrder).length;
  const availableCount = drivers.filter(isAvailableDriver).length;

  const pendingOrders = safeOrders.filter(isPendingOrder);
  const activeOrders = safeOrders.filter(isActiveOrder);
  const assignedOrders = safeOrders.filter(isAssignedOrder);
  const activeOrdersByDriver = activeOrders.reduce((acc, order) => {
    const driverId = Number(getOrderDriverId(order));
    if (Number.isFinite(driverId)) {
      acc.set(driverId, (acc.get(driverId) || 0) + 1);
    }
    return acc;
  }, new Map());

  const activeRouteInfoByDriver = activeOrders.reduce((acc, order) => {
    const driverId = Number(getOrderDriverId(order));
    if (!Number.isFinite(driverId)) {
      return acc;
    }

    const current = acc.get(driverId) || { routeId: null, orderCount: 0 };
    const routeId = getOrderRouteId(order);
    acc.set(driverId, {
      routeId: current.routeId || routeId || null,
      orderCount: current.orderCount + 1,
    });

    return acc;
  }, new Map());

  const isOperationallyAvailableState = (status) => ['disponible', 'activo', 'active', 'available'].includes(status);
  const isDriverOutsideRadius = (driver) => {
    const distance = Number(driver?.distancia_al_centro_demanda_km);
    const maxRadius = Number(driver?.radio_maximo_km);
    return Number.isFinite(distance) && Number.isFinite(maxRadius) && distance > maxRadius;
  };

  const getDriverLocationStatus = (driver) => {
    const coords = getDriverCoordinates(driver);
    if (!coords) return { label: 'Sin ubicación', icon: '🔴', className: 'sin-ubicacion' };
    if (isDriverOutsideRadius(driver)) {
      return { label: 'Fuera del radio', icon: '🟡', className: 'fuera-radio' };
    }
    return { label: 'Ubicación válida', icon: '🟢', className: 'ubicacion-valida' };
  };

  const getDriverOperationalStatus = (driver) => {
    const activeCount = activeOrdersByDriver.get(Number(driver.id)) || 0;
    const status = normalizeText(driver.status || driver.estado);
    const isManuallyDisabled = driver.disponible !== true;
    const isInactive = !isOperationallyAvailableState(status);

    if (activeCount > 0 || status === 'ocupado') {
      return { label: 'En entrega', icon: '🚗', className: 'en-entrega', badge: 'warning' };
    }
    if (isManuallyDisabled) {
      return { label: 'No disponible', icon: '🔴', className: 'no-disponible', badge: 'danger' };
    }
    if (isInactive) {
      return { label: 'Inactivo', icon: '⚪', className: 'inactivo', badge: 'secondary' };
    }
    return { label: 'Disponible', icon: '🟢', className: 'disponible', badge: 'success' };
  };

  const canDriverReceiveOrders = (driver) => {
    const activeCount = activeOrdersByDriver.get(Number(driver.id)) || 0;
    const status = normalizeText(driver.status || driver.estado);
    const hasCoordinates = Boolean(getDriverCoordinates(driver));
    const outsideRadius = isDriverOutsideRadius(driver);

    return (
      driver.disponible === true
      && isOperationallyAvailableState(status)
      && activeCount === 0
      && hasCoordinates
      && !outsideRadius
    );
  };

  const canOptimizeRoutes = (driver) => {
    return canDriverReceiveOrders(driver);
  };

  const getDriverReason = (driver) => {
    const activeCount = activeOrdersByDriver.get(Number(driver.id)) || 0;
    const hasCoordinates = Boolean(getDriverCoordinates(driver));
    const outsideRadius = isDriverOutsideRadius(driver);

    if (activeCount > 0) {
      return 'Está entregando una ruta activa.';
    }
    if (driver.disponible !== true) {
      return 'Fue deshabilitado manualmente.';
    }
    const status = normalizeText(driver.status || driver.estado);
    if (!isOperationallyAvailableState(status)) {
      return 'Estado inactivo en sistema.';
    }
    if (!hasCoordinates) {
      return 'No tiene coordenadas registradas.';
    }
    if (outsideRadius) {
      return 'Está fuera del radio permitido.';
    }
    return 'Disponible para nuevas asignaciones.';
  };

  const getDriverAssignmentType = (driver) => {
    const operationalStatus = getDriverOperationalStatus(driver);
    const hasCoordinates = Boolean(getDriverCoordinates(driver));

    if (operationalStatus.label === 'En entrega' || operationalStatus.label === 'No disponible') {
      return { label: 'No asignable', className: 'none' };
    }
    if (canOptimizeRoutes(driver)) {
      return { label: 'Manual y optimización', className: 'both' };
    }
    if (driver.disponible === true && hasCoordinates) {
      return { label: 'Manual y optimización', className: 'both' };
    }
    if (driver.disponible === true && !hasCoordinates) {
      return { label: 'Solo manual', className: 'manual' };
    }
    return { label: 'No asignable', className: 'none' };
  };

  const driverStats = drivers.reduce((acc, driver) => {
    const operationalStatus = getDriverOperationalStatus(driver);
    const locationStatus = getDriverLocationStatus(driver);

    acc.total += 1;
    if (operationalStatus.label === 'Disponible') acc.available += 1;
    if (operationalStatus.label === 'En entrega') acc.inDelivery += 1;
    if (locationStatus.label === 'Sin ubicación') acc.noLocation += 1;
    if (locationStatus.label === 'Fuera del radio') acc.outsideRadius += 1;
    if (canOptimizeRoutes(driver)) acc.canOptimize += 1;
    return acc;
  }, { total: 0, available: 0, inDelivery: 0, noLocation: 0, outsideRadius: 0, canOptimize: 0 });

  const handleOpenManualAssign = (order) => {
    setAssignmentError('');
    setAssignmentSuccess('');
    setManualAssignModal({ isOpen: true, order });
  };

  const handleCloseManualAssign = () => {
    setManualAssignModal({ isOpen: false, order: null });
    setAssignmentError('');
  };

  const handleConfirmManualAssign = async (orderId, driverId) => {
    setAssignmentLoading(true);
    setAssignmentError('');
    try {
      await assignOrder(orderId, driverId);
      setAssignmentSuccess('Pedido asignado correctamente');
      setTimeout(() => setAssignmentSuccess(''), 3000);
      handleCloseManualAssign();
    } catch (error) {
      const errorMsg = error.message || 'Error al asignar el pedido';
      setAssignmentError(errorMsg);
    } finally {
      setAssignmentLoading(false);
    }
  };

  const handleAssignOrders = async () => {
    setIsAssigning(true);
    await assignOrders();
    setIsAssigning(false);
  };

  const handleRefreshImportedData = async () => {
    setImportError('');
    setImportMessage('');
    try {
      await refreshData();
      setImportMessage('Datos actualizados desde el backend.');
    } catch (error) {
      setImportError(error.message || 'No se pudieron actualizar los datos.');
    }
  };

  const handleImportExcel = async () => {
    setImportError('');
    setImportMessage('');
    setImportSummary(null);

    if (!selectedFile) {
      setImportError('Selecciona un archivo Excel antes de importar.');
      return;
    }

    setIsImporting(true);
    try {
      const result = await importExcelData(selectedFile);
      setImportSummary(result);
      setImportMessage(result.message || 'Importacion completada.');
      setSelectedFile(null);
    } catch (error) {
      setImportError(error.message || 'No se pudo importar el Excel.');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Dashboard de asignacion</h1>
        <p>Pedidos, repartidores y optimizacion multi-pedido en una sola vista.</p>
        <div className="import-toolbar mt-4">
          <button className="btn-secondary" onClick={handleRefreshImportedData} disabled={loading || isImporting}>
            {loading ? 'Actualizando...' : 'Actualizar datos'}
          </button>
          <input
            type="file"
            accept=".xlsx,.xls"
            onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
          />
          <button className="btn-primary" onClick={handleImportExcel} disabled={isImporting}>
            {isImporting ? 'Importando...' : 'Importar Excel'}
          </button>
        </div>
        {importMessage && <div className="success-message mt-4">{importMessage}</div>}
        {importError && <div className="error-message mt-4">{importError}</div>}
        {importSummary && (
          <div className="import-summary">
            {!!importSummary.sheets_detected?.length && (
              <p>Hojas detectadas: {importSummary.sheets_detected.join(', ')}</p>
            )}
            <p>Creados: {JSON.stringify(importSummary.created)}</p>
            <p>Actualizados: {JSON.stringify(importSummary.updated)}</p>
            {!!importSummary.warnings?.length && <p>Advertencias: {importSummary.warnings.join(' | ')}</p>}
            {!!importSummary.errors?.length && <p>Errores: {importSummary.errors.join(' | ')}</p>}
          </div>
        )}
      </header>

      <main className="optimizer-grid">
        <PendingOrdersMap
          orders={safeOrders}
          warehouses={safeWarehouses}
          driverLocation={driverLocation}
          selectedDriver={selectedOptimizerDriver}
          isAdminMode
          onDriverLocationDraftChange={setDriverLocation}
          selectedOrderIds={optimization?.optimizer?.pedidos_seleccionados || []}
          selectedWarehouseId={optimization?.optimizer?.aliado_id}
          routeGeometry={optimization?.optimizer?.geometria}
          routeStops={optimization?.route?.paradas || []}
          optimization={optimization}
          routes={safeRoutes}
        />
        <RouteOptimizerPanel
          onDriverLocationChange={setDriverLocation}
          onOptimized={setOptimization}
          externalDriverLocation={driverLocation}
          onSelectedDriverChange={setSelectedOptimizerDriver}
        />
      </main>

      <main className="main-grid mt-4">
        <section className="panel">
          <h2>Pedidos activos <span className="count">{activeOrders.length}</span></h2>
          <div className="list-container">
            {activeOrders.length === 0 ? (
              <p className="text-muted">No hay pedidos activos</p>
            ) : activeOrders.map((order) => (
              <div key={order.id} className="card">
                <div className="card-info">
                  <h3>Pedido #{order.id} - {getOrderCustomer(order)}</h3>
                  <p>{getOrderDestination(order)}</p>
                  <p>Repartidor: {getOrderDriverName(order)}</p>
                  <p>Ruta: {getOrderRouteId(order) ? `Ruta #${getOrderRouteId(order)}` : 'Sin ruta'} | Orden: {getOrderStopOrder(order) ? `#${getOrderStopOrder(order)}` : 'N/A'}</p>
                  <p>Prioridad: {getOrderPriority(order)} | ETA: {order.tiempo_estimado_desde_anterior_mins || 'N/A'} min</p>
                </div>
                <div className={`badge ${getOrderStatus(order).toLowerCase().replace(' ', '-')}`}>
                  {getOrderStatus(order)}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Pedidos pendientes <span className="count">{pendingCount}</span></h2>
          {assignmentSuccess && <div className="success-message mt-2">{assignmentSuccess}</div>}
          <div className="list-container">
            {pendingOrders.length === 0 ? (
              <p className="text-muted">No hay pedidos pendientes</p>
            ) : (
              pendingOrders.map((order) => (
                <div key={order.id} className="card">
                  <div className="card-info">
                    <h3>#{order.id} - {getOrderCustomer(order)}</h3>
                    <p>{getOrderDestination(order)}</p>
                    <p>Peso: {getOrderWeight(order)} kg | Prioridad: {getOrderPriority(order)}</p>
                  </div>
                  <div className="card-actions">
                    <button
                      className="btn-small btn-primary"
                      onClick={() => handleOpenManualAssign(order)}
                      disabled={assignmentLoading}
                    >
                      Asignar manualmente
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="panel">
          <h2>Pedidos asignados <span className="count">{assignedOrders.length}</span></h2>
          <div className="list-container">
            {assignedOrders.length === 0 ? (
              <p className="text-muted">No hay pedidos asignados</p>
            ) : (
              assignedOrders.map((order) => (
                <div key={order.id} className="card">
                  <div className="card-info">
                    <h3>#{order.id} - {getOrderCustomer(order)}</h3>
                    <p>{getOrderDestination(order)}</p>
                    <p>Repartidor: {getOrderDriverId(order) || 'Asignado'}</p>
                  </div>
                  <div className="badge asignado">
                    {getOrderStatus(order)}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="panel">
          <h2>Repartidores en zona <span className="count">{drivers.length}</span></h2>
          {/* Resumen estadísticas */}
          <div className="drivers-summary-cards mt-4">
            <div className="summary-card">
              <span className="summary-label">Total</span>
              <span className="summary-value">{driverStats.total}</span>
            </div>
            <div className="summary-card available">
              <span className="summary-label">Disponibles</span>
              <span className="summary-value">🟢 {driverStats.available}</span>
            </div>
            <div className="summary-card in-delivery">
              <span className="summary-label">En entrega</span>
              <span className="summary-value">🚗 {driverStats.inDelivery}</span>
            </div>
            <div className="summary-card no-location">
              <span className="summary-label">Sin ubicación</span>
              <span className="summary-value">🔴 {driverStats.noLocation}</span>
            </div>
            <div className="summary-card outside-radius">
              <span className="summary-label">Fuera de radio</span>
              <span className="summary-value">🟡 {driverStats.outsideRadius}</span>
            </div>
            <div className="summary-card can-optimize">
              <span className="summary-label">Aptos optimización</span>
              <span className="summary-value">✨ {driverStats.canOptimize}</span>
            </div>
          </div>

          {/* Tabla rediseñada */}
          <div className="drivers-zone-table mt-4">
            <div className="drivers-zone-head">
              <span>Repartidor</span>
              <span>Estado operativo</span>
              <span>Ubicación</span>
              <span>Ruta activa</span>
              <span>Puede recibir pedidos</span>
              <span>Motivo</span>
              <span>Tipo de asignación</span>
            </div>
            {drivers.map((driver) => {
              const operationalStatus = getDriverOperationalStatus(driver);
              const locationStatus = getDriverLocationStatus(driver);
              const routeInfo = activeRouteInfoByDriver.get(Number(driver.id)) || { routeId: null, orderCount: 0 };
              const canReceive = canDriverReceiveOrders(driver);
              const assignmentType = getDriverAssignmentType(driver);
              const reason = getDriverReason(driver);

              return (
                <div key={driver.id} className="drivers-zone-row">
                  {/* Repartidor */}
                  <div className="driver-name-cell">
                    <strong>{driver.name || driver.nombre || 'Repartidor'}</strong>
                  </div>

                  {/* Estado operativo */}
                  <div>
                    <span className={`driver-operational-badge driver-operational-${operationalStatus.badge}`} title={operationalStatus.label}>
                      {operationalStatus.icon} {operationalStatus.label}
                    </span>
                  </div>

                  {/* Ubicación */}
                  <div title={locationStatus.label}>
                    <span className={`location-badge ${locationStatus.className}`}>
                      {locationStatus.icon} {locationStatus.label}
                    </span>
                  </div>

                  {/* Ruta activa */}
                  <div>
                    {routeInfo.orderCount > 0 ? (
                      <span className="active-route-badge">
                        Sí {routeInfo.routeId ? `· Ruta #${routeInfo.routeId}` : ''} · {routeInfo.orderCount} pedido{routeInfo.orderCount > 1 ? 's' : ''}
                      </span>
                    ) : (
                      <span className="text-muted">No</span>
                    )}
                  </div>

                  {/* Puede recibir */}
                  <div>
                    <span
                      className={`capability-badge ${canReceive ? 'can-receive' : 'cannot-receive'}`}
                      title={reason}
                    >
                      {canReceive ? '🟢 Sí puede' : '🔴 No puede'}
                    </span>
                  </div>

                  {/* Motivo */}
                  <div className="motivo-cell">
                    <small title={reason}>{reason}</small>
                  </div>

                  {/* Tipo asignación */}
                  <div>
                    <span className={`assignment-badge assignment-${assignmentType.className}`}>
                      {assignmentType.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>



          <div className="actions">
            <button
              className="btn-primary"
              onClick={handleAssignOrders}
              disabled={isAssigning || pendingCount === 0 || availableCount === 0}
            >
              {isAssigning ? 'Procesando...' : 'Asignacion simple heredada'}
            </button>
          </div>
        </section>
      </main>

      <ManualAssignModal
        isOpen={manualAssignModal.isOpen}
        order={manualAssignModal.order}
        drivers={drivers}
        onAssign={handleConfirmManualAssign}
        onClose={handleCloseManualAssign}
        isLoading={assignmentLoading}
        error={assignmentError}
      />
    </div>
  );
};
