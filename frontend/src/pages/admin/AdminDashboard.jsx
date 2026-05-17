import { useState } from 'react';
import { PendingOrdersMap } from '../../components/PendingOrdersMap';
import { RouteOptimizerPanel } from '../../components/RouteOptimizerPanel';
import { useAppContext } from '../../context/AppContext';

export const AdminDashboard = () => {
  const { orders, warehouses, getDrivers, assignOrders, refreshData, importExcelData, optimizeBatchRoutes, loading } = useAppContext();
  const [isAssigning, setIsAssigning] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [importMessage, setImportMessage] = useState('');
  const [importError, setImportError] = useState('');
  const [importSummary, setImportSummary] = useState(null);
  const [optimization, setOptimization] = useState(null);
  const [driverLocation, setDriverLocation] = useState({ lat: 4.7110, lng: -74.0721 });

  const drivers = getDrivers();
  const pendingCount = orders.filter((order) => order.status === 'Pendiente' || order.estado === 'Pendiente').length;
  const availableCount = drivers.filter((driver) => driver.status === 'Disponible').length;

  const handleAssignOrders = async () => {
    setIsAssigning(true);
    await assignOrders();
    setIsAssigning(false);
  };

  const handleBatchOptimize = async () => {
    setIsAssigning(true);
    setImportError('');
    setImportMessage('');
    try {
      const result = await optimizeBatchRoutes();
      setImportMessage(result.mensaje || 'Optimización en lote completada con éxito.');
      setImportSummary({
        created: { rutas: result.rutas_creadas?.length || 0 },
        updated: {},
        warnings: [],
        errors: []
      });
    } catch (error) {
      setImportError(error.message || 'No se pudo realizar la optimización en lote.');
    } finally {
      setIsAssigning(false);
    }
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
          <div className="import-summary panel mt-4" style={{ padding: '1.5rem', background: 'rgba(56, 189, 248, 0.05)', borderColor: 'rgba(56, 189, 248, 0.2)' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: 'var(--accent-neon)' }}>Resumen de importación / optimización</h3>
            <div className="metric-grid">
              <div className="metric">
                <span>Clientes creados</span>
                <strong>{importSummary.created?.clientes || 0}</strong>
              </div>
              <div className="metric">
                <span>Pedidos creados</span>
                <strong>{importSummary.created?.pedidos || 0}</strong>
              </div>
              <div className="metric">
                <span>Rutas auto-creadas</span>
                <strong>{importSummary.created?.rutas || 0}</strong>
              </div>
            </div>
            {!!importSummary.warnings?.length && (
              <div className="warning-message mt-4">
                <strong>Advertencias:</strong>
                <ul style={{ margin: '0.5rem 0 0 1rem', padding: 0 }}>
                  {importSummary.warnings.map((w, idx) => <li key={idx}>{w}</li>)}
                </ul>
              </div>
            )}
            {!!importSummary.errors?.length && (
              <div className="error-message mt-4">
                <strong>Errores:</strong>
                <ul style={{ margin: '0.5rem 0 0 1rem', padding: 0 }}>
                  {importSummary.errors.map((e, idx) => <li key={idx}>{e}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </header>

      <main className="optimizer-grid">
        <PendingOrdersMap
          orders={orders}
          warehouses={warehouses}
          driverLocation={optimization?.optimizer?.start || driverLocation}
          selectedOrderIds={optimization?.optimizer?.pedidos_seleccionados || []}
          selectedWarehouseId={optimization?.optimizer?.aliado_id}
          routeGeometry={optimization?.optimizer?.geometria}
          routeStops={optimization?.route?.paradas || []}
        />
        <RouteOptimizerPanel
          onDriverLocationChange={setDriverLocation}
          onOptimized={setOptimization}
        />
      </main>

      <main className="main-grid mt-4">
        <section className="panel">
          <h2>Pedidos activos <span className="count">{orders.length}</span></h2>
          <div className="list-container">
            {orders.map((order) => (
              <div key={order.id} className="card">
                <div className="card-info">
                  <h3>{order.customer}</h3>
                  <p>{order.destination}</p>
                  {order.driverId && <p>Repartidor ID: {order.driverId}</p>}
                </div>
                <div className={`badge ${(order.status || order.estado).toLowerCase().replace(' ', '-')}`}>
                  {order.status || order.estado}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Repartidores en zona <span className="count">{drivers.length}</span></h2>
          <div className="list-container">
            {drivers.map((driver) => (
              <div key={driver.id} className="card">
                <div className="card-info">
                  <h3>{driver.name}</h3>
                  <p>{driver.location}</p>
                </div>
                <div className={`badge ${driver.status.toLowerCase()}`}>
                  {driver.status}
                </div>
              </div>
            ))}
          </div>

          <div className="actions split-actions mt-4">
            <button
              className="btn-secondary"
              onClick={handleAssignOrders}
              disabled={isAssigning || pendingCount === 0 || availableCount === 0}
            >
              {isAssigning ? 'Procesando...' : 'Asignación simple'}
            </button>
            <button
              className="btn-primary"
              onClick={handleBatchOptimize}
              disabled={isAssigning || pendingCount === 0 || availableCount === 0}
            >
              {isAssigning ? 'Optimizando...' : 'Optimización en Lote'}
            </button>
          </div>
        </section>
      </main>
    </div>
  );
};
