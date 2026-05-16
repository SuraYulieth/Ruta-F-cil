import { useState } from 'react';
import { AddressAutocompleteMap } from '../../components/AddressAutocompleteMap';
import { useAppContext } from '../../context/AppContext';

export const CreateRoute = () => {
  const { addOrder } = useAppContext();
  const [form, setForm] = useState({
    customer: '',
    destination: '',
    latitude: '',
    longitude: '',
    priority: 'normal',
    weightKg: '0',
  });
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [warningMsg, setWarningMsg] = useState('');

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMsg('');
    setWarningMsg('');
    if (!form.destination) {
      setErrorMsg('La direccion de destino es obligatoria.');
      return;
    }
    if (!form.latitude || !form.longitude) {
      setWarningMsg('El pedido se guardara sin coordenadas. Para verlo en mapa y optimizarlo, selecciona una sugerencia de Google Maps despues.');
    }
    try {
      await addOrder({
        ...form,
        latitude: form.latitude ? Number(form.latitude) : null,
        longitude: form.longitude ? Number(form.longitude) : null,
        weightKg: Number(form.weightKg || 0),
      });
      setForm({
        customer: '',
        destination: '',
        latitude: '',
        longitude: '',
        priority: 'normal',
        weightKg: '0',
      });
      setSuccessMsg('Pedido creado exitosamente');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (error) {
      setErrorMsg(error.message || 'No se pudo crear el pedido.');
    }
  };

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Crear nuevo pedido</h1>
        <p>Registra destino con Google Places; las coordenadas se guardan automaticamente.</p>
      </header>

      <section className="panel form-panel">
        <form onSubmit={handleSubmit} className="custom-form">
          {successMsg && <div className="success-message">{successMsg}</div>}
          {warningMsg && <div className="warning-message">{warningMsg}</div>}
          {errorMsg && <div className="error-message">{errorMsg}</div>}

          <div className="form-group">
            <label>Cliente / negocio</label>
            <input
              type="text"
              value={form.customer}
              onChange={(event) => updateField('customer', event.target.value)}
              placeholder="Ej: Farmacia Central"
              required
            />
          </div>

          <AddressAutocompleteMap
            label="Direccion de destino"
            value={form.destination}
            latitude={form.latitude}
            longitude={form.longitude}
            onAddressChange={(address) => {
              setForm((current) => ({
                ...current,
                destination: address,
                latitude: '',
                longitude: '',
              }));
            }}
            onLocationChange={({ lat, lng }) => {
              setForm((current) => ({
                ...current,
                latitude: lat,
                longitude: lng,
              }));
            }}
          />

          <div className="form-row">
            <div className="form-group">
              <label>Prioridad</label>
              <select value={form.priority} onChange={(event) => updateField('priority', event.target.value)}>
                <option value="baja">Baja</option>
                <option value="normal">Normal</option>
                <option value="alta">Alta</option>
                <option value="urgente">Urgente</option>
              </select>
            </div>
            <div className="form-group">
              <label>Peso kg</label>
              <input
                value={form.weightKg}
                onChange={(event) => updateField('weightKg', event.target.value)}
                placeholder="2.5"
              />
            </div>
          </div>

          <button type="submit" className="btn-primary mt-4">
            Registrar pedido
          </button>
        </form>
      </section>
    </div>
  );
};
