import { useState } from 'react';
import { useAppContext } from '../../context/AppContext';

export const CreateRoute = () => {
  const { addOrder } = useAppContext();
  const [customer, setCustomer] = useState('');
  const [destination, setDestination] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    await addOrder({ customer, destination });
    setCustomer('');
    setDestination('');
    setSuccessMsg('Ruta creada exitosamente');
    setTimeout(() => setSuccessMsg(''), 3000);
  };

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Crear Nueva Ruta</h1>
        <p>Añade un nuevo pedido al sistema para ser asignado.</p>
      </header>

      <section className="panel form-panel">
        <form onSubmit={handleSubmit} className="custom-form">
          {successMsg && <div className="success-message">{successMsg}</div>}
          
          <div className="form-group">
            <label>Cliente / Negocio</label>
            <input 
              type="text" 
              value={customer} 
              onChange={(e) => setCustomer(e.target.value)} 
              placeholder="Ej: Farmacia Central"
              required 
            />
          </div>

          <div className="form-group">
            <label>Dirección de Destino</label>
            <input 
              type="text" 
              value={destination} 
              onChange={(e) => setDestination(e.target.value)} 
              placeholder="Ej: Calle 50 # 10-20"
              required 
            />
          </div>

          <button type="submit" className="btn-primary mt-4">
            ➕ Registrar Ruta
          </button>
        </form>
      </section>
    </div>
  );
};
