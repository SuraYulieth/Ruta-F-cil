import { useMemo, useState } from 'react';

const classifyUnassigned = (motivo = '') => {
  const lower = motivo.toLowerCase();
  if (lower.includes('peso') || lower.includes('capacidad')) {
    return { label: 'No asignados por capacidad', className: 'capacity' };
  }
  if (lower.includes('radio') || lower.includes('cobertura') || lower.includes('repartidores disponibles')) {
    return { label: 'No asignados por cobertura', className: 'coverage' };
  }
  return { label: 'No asignados por reglas logisticas', className: 'rules' };
};

const buildUnassignedSummary = (orders = []) => {
  const grouped = new Map();
  orders.forEach((item) => {
    const motivo = item?.motivo || 'Sin motivo especificado.';
    const current = grouped.get(motivo) || { motivo, cantidad: 0, pedidos: [] };
    current.cantidad += 1;
    if (item?.pedido_id !== undefined && item?.pedido_id !== null) {
      current.pedidos.push(item.pedido_id);
    }
    grouped.set(motivo, current);
  });
  return Array.from(grouped.values());
};

export const RouteSummary = ({ optimization }) => {
  const [showTechnicalDetail, setShowTechnicalDetail] = useState(false);
  const [showDriverDetail, setShowDriverDetail] = useState(false);
  const optimizer = optimization?.optimizer || null;
  const decision = optimization?.decision;
  const metrics = optimization?.metrics;
  const summary = optimizer?.summary || {};
  const routes = optimizer?.routes?.length ? optimizer.routes : optimizer?.route ? [optimizer.route] : [];
  const unassignedOrders = optimizer?.unassigned_orders || optimizer?.pedidos_descartados || [];
  const unassignedSummary = useMemo(
    () => optimizer?.unassigned_summary?.length ? optimizer.unassigned_summary : buildUnassignedSummary(unassignedOrders),
    [optimizer?.unassigned_summary, unassignedOrders],
  );
  const unassignedTotal = unassignedSummary.reduce((total, item) => total + Number(item.cantidad || 0), 0);
  const driverDiagnostics = optimizer?.driver_diagnostics || optimization?.decision?.driver_diagnostics || null;
  const hasDriverDiagnostics = Boolean(driverDiagnostics?.total_repartidores);
  const coverageRecommendation = driverDiagnostics?.coverage_recommendation || null;
  const outsideRadiusDrivers = (driverDiagnostics?.detalle || []).filter((driver) => (
    driver.distancia_al_centro_demanda_km !== null
    && driver.distancia_al_centro_demanda_km !== undefined
    && Number(driver.distancia_al_centro_demanda_km) > Number(driver.radio_maximo_km || 0)
  ));

  if (!optimizer) {
    return (
      <div className="route-summary empty-state">
        Optimiza una ruta para ver distancia, tiempo y capacidad estimada.
      </div>
    );
  }

  return (
    <div className="route-summary">
      <div className="metric-grid">
        <div className="metric">
          <span>Total pedidos</span>
          <strong>{summary.total_pedidos ?? optimizer.pedidos_seleccionados?.length ?? 0}</strong>
        </div>
        <div className="metric">
          <span>Rutas</span>
          <strong>{summary.rutas_creadas ?? routes.length}</strong>
        </div>
        <div className="metric">
          <span>Asignados</span>
          <strong>{summary.pedidos_asignados ?? optimizer.pedidos_seleccionados?.length ?? 0}</strong>
        </div>
        <div className="metric">
          <span>No asignados</span>
          <strong>{summary.pedidos_no_asignados ?? unassignedOrders.length}</strong>
        </div>
        <div className="metric">
          <span>Distancia</span>
          <strong>{optimizer.distancia_total_km} km</strong>
        </div>
        <div className="metric">
          <span>Tiempo</span>
          <strong>{optimizer.duracion_total_mins} min</strong>
        </div>
        <div className="metric">
          <span>Capacidad</span>
          <strong>{optimizer.capacidad_usada_kg} kg</strong>
        </div>
      </div>

      <div className="decision-box">
        <h3>Decision inteligente</h3>
        <p>{decision?.explicacion}</p>
        {decision?.eficiencia && <p>{decision.eficiencia}</p>}
        {decision?.repartidor?.nombre && (
          <p className="hint-text">Repartidor sugerido: {decision.repartidor.nombre}</p>
        )}
        {decision?.bodega?.nombre && (
          <p className="hint-text">Bodega sugerida: {decision.bodega.nombre}</p>
        )}
        {decision?.alertas?.map((alert) => (
          <p key={alert} className="warning-text">{alert}</p>
        ))}
        {decision?.recomendaciones?.map((recommendation) => (
          <p key={recommendation} className="hint-text">{recommendation}</p>
        ))}
      </div>

      {routes.length > 0 && (
        <div className="decision-box">
          <h3>Rutas generadas</h3>
          {routes.map((route, index) => (
            <div key={`${route.repartidor_id || index}-${index}`} className="route-summary-card">
              <p className="hint-text">
                Ruta {index + 1} - Repartidor: {route.repartidor_nombre || route.repartidor_id || 'Sin reparto'}
              </p>
              <p>Pedidos: {(route.pedidos_seleccionados || []).join(', ')}</p>
              <p>
                Distancia: {route.distancia_total_km} km | Tiempo: {route.duracion_total_mins} min | Bodega: {route.aliado_nombre || 'Sin bodega'}
              </p>
            </div>
          ))}
        </div>
      )}

      {unassignedTotal > 0 && (
        <div className="decision-box">
          <div className="summary-title-row">
            <h3>Pedidos no asignados: {unassignedTotal}</h3>
            <button
              type="button"
              className="btn-secondary compact"
              onClick={() => setShowTechnicalDetail((current) => !current)}
            >
              {showTechnicalDetail ? 'Ocultar detalle tecnico' : 'Ver detalle tecnico'}
            </button>
          </div>
          <div className="unassigned-summary-list">
            {unassignedSummary.map((item) => {
              const type = classifyUnassigned(item.motivo);
              return (
                <article key={item.motivo} className={`unassigned-summary-item ${type.className}`}>
                  <span>{type.label}</span>
                  <strong>{item.cantidad}</strong>
                  <p>{item.motivo}</p>
                </article>
              );
            })}
          </div>
          {showTechnicalDetail && (
            <div className="technical-detail-list">
              {unassignedOrders.map((item) => (
                <p key={`${item.pedido_id}-${item.motivo}`} className="warning-text">
                  Pedido #{item.pedido_id}: {item.motivo}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {hasDriverDiagnostics && routes.length === 0 && (
        <div className="decision-box driver-diagnostic-box">
          <div className="summary-title-row">
            <div>
              <h3>Diagnostico de repartidores</h3>
              <p className="hint-text">
                Actualmente no hay repartidores aptos para esta optimizacion. Activa un repartidor,
                verifica que tenga coordenadas y que no este en una ruta activa.
              </p>
            </div>
            <button
              type="button"
              className="btn-secondary compact"
              onClick={() => setShowDriverDetail((current) => !current)}
            >
              {showDriverDetail ? 'Ocultar detalle tecnico' : 'Ver detalle tecnico'}
            </button>
          </div>

          <div className="driver-diagnostic-grid">
            <div><span>Total repartidores</span><strong>{driverDiagnostics.total_repartidores || 0}</strong></div>
            <div><span>Disponibles</span><strong>{driverDiagnostics.disponibles || 0}</strong></div>
            <div><span>Deshabilitados</span><strong>{driverDiagnostics.deshabilitados || 0}</strong></div>
            <div><span>En entrega</span><strong>{driverDiagnostics.en_entrega || 0}</strong></div>
            <div><span>Sin coordenadas</span><strong>{driverDiagnostics.sin_coordenadas || 0}</strong></div>
            <div><span>Fuera de radio</span><strong>{driverDiagnostics.fuera_de_radio || 0}</strong></div>
            <div><span>Aptos</span><strong>{driverDiagnostics.aptos_para_optimizar || 0}</strong></div>
          </div>

          {coverageRecommendation?.centro_demanda && (
            <div className="coverage-recommendation-card">
              <h3>¿Donde debe estar el repartidor?</h3>
              <p>{coverageRecommendation.mensaje}</p>
              <div className="coverage-recommendation-metrics">
                <span>Latitud: <strong>{coverageRecommendation.centro_demanda.latitud}</strong></span>
                <span>Longitud: <strong>{coverageRecommendation.centro_demanda.longitud}</strong></span>
                <span>Radio permitido: <strong>{coverageRecommendation.radio_maximo_km} km</strong></span>
              </div>
              {coverageRecommendation.google_maps_url && (
                <a
                  className="btn-secondary compact coverage-map-link"
                  href={coverageRecommendation.google_maps_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Abrir en Google Maps
                </a>
              )}
            </div>
          )}

          {showDriverDetail && (
            <div className="driver-diagnostic-table">
              <div className="driver-diagnostic-head">
                <span>Repartidor</span>
                <span>Estado</span>
                <span>Coordenadas</span>
                <span>Ruta activa</span>
                <span>Motivo</span>
              </div>
              {(driverDiagnostics.detalle || []).map((driver) => (
                <div key={driver.id} className="driver-diagnostic-row">
                  <span>{driver.nombre}</span>
                  <span>{driver.estado || 'Sin estado'}</span>
                  <span>{driver.tiene_coordenadas ? 'Si' : 'No'}</span>
                  <span>{driver.tiene_ruta_activa ? 'Si' : 'No'}</span>
                  <span>{driver.motivo}</span>
                </div>
              ))}
            </div>
          )}

          {outsideRadiusDrivers.length > 0 && (
            <details className="outside-radius-detail">
              <summary>Ver repartidores fuera de radio</summary>
              {outsideRadiusDrivers.map((driver) => (
                <article key={`outside-${driver.id}`}>
                  <strong>{driver.nombre}</strong>
                  <p>
                    Actual: {driver.coordenadas_actuales?.latitud}, {driver.coordenadas_actuales?.longitud}
                  </p>
                  <p>
                    Debe acercarse a: {driver.coordenadas_recomendadas?.latitud}, {driver.coordenadas_recomendadas?.longitud}
                  </p>
                  <p>
                    Distancia actual: {driver.distancia_al_centro_demanda_km} km | Radio maximo: {driver.radio_maximo_km} km
                  </p>
                  <p>{driver.motivo}</p>
                </article>
              ))}
            </details>
          )}
        </div>
      )}

      {metrics && (
        <div className="decision-box">
          <h3>Evidencia ABP</h3>
          <p>Complejidad: mejor {metrics.complejidad?.mejor_caso}, promedio {metrics.complejidad?.caso_promedio}, peor {metrics.complejidad?.peor_caso}.</p>
          <p>{metrics.complejidad?.detalle}</p>
          <p>
            Manual Excel: {metrics.comparacion_manual_excel?.distancia_manual_estimada_km} km estimados.
            Sistema: {metrics.comparacion_manual_excel?.distancia_sistema_km} km.
          </p>
          <p>Ahorro estimado: {metrics.comparacion_manual_excel?.ahorro_distancia_estimado_km} km.</p>
        </div>
      )}
    </div>
  );
};
