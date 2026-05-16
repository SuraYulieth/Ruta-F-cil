import { useState } from 'react';
import { AddressAutocompleteMap } from '../../components/AddressAutocompleteMap';
import { useAppContext } from '../../context/AppContext';

export const ManageUsers = () => {
  const { users, addUser, addWarehouse, addDriverProfile } = useAppContext();
  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('driver');
  const [phone, setPhone] = useState('');
  const [capacity, setCapacity] = useState('15');
  const [address, setAddress] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [warningMsg, setWarningMsg] = useState('');

  const resetLocationFields = () => {
    setPhone('');
    setCapacity('15');
    setAddress('');
    setLatitude('');
    setLongitude('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSuccessMsg('');
    setErrorMsg('');
    setWarningMsg('');

    try {
      if ((role === 'driver' || role === 'aliado') && !address) {
        setErrorMsg('La direccion es obligatoria para repartidores y bodegas.');
        return;
      }
      if ((role === 'driver' || role === 'aliado') && (!latitude || !longitude)) {
        setWarningMsg('Se guardara la direccion sin coordenadas. No aparecera correctamente en mapa hasta seleccionar una sugerencia valida.');
      }

      const createdUser = await addUser({ nombre: name, username, password, role, ubicacion: address || undefined });

      if (role === 'aliado') {
        await addWarehouse({
          user: createdUser.id,
          direccion: address,
          latitud: latitude ? Number(latitude) : null,
          longitud: longitude ? Number(longitude) : null,
        });
      }

      if (role === 'driver') {
        await addDriverProfile({
          user: createdUser.id,
          telefono: phone,
          latitud_actual: latitude ? Number(latitude) : null,
          longitud_actual: longitude ? Number(longitude) : null,
          capacidad_maxima_kg: Number(capacity || 15),
        });
      }

      setName('');
      setUsername('');
      setPassword('');
      resetLocationFields();
      setSuccessMsg('Usuario creado exitosamente');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (error) {
      setErrorMsg(error.message || 'No se pudo crear el usuario.');
    }
  };

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Gestion de Usuarios</h1>
        <p>Administra roles, bodegas y repartidores con ubicacion de Google Maps.</p>
      </header>

      <div className="main-grid">
        <section className="panel form-panel">
          <h2>Crear Nuevo Usuario</h2>
          <form onSubmit={handleSubmit} className="custom-form">
            {successMsg && <div className="success-message">{successMsg}</div>}
            {warningMsg && <div className="warning-message">{warningMsg}</div>}
            {errorMsg && <div className="error-message">{errorMsg}</div>}

            <div className="form-group">
              <label>Nombre Completo</label>
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Usuario (Login)</label>
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Contrasena</label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Rol</label>
              <select
                value={role}
                onChange={(event) => {
                  setRole(event.target.value);
                  resetLocationFields();
                }}
              >
                <option value="driver">Repartidor</option>
                <option value="aliado">Aliado / Bodega</option>
                <option value="admin">Administrador</option>
              </select>
            </div>

            {(role === 'driver' || role === 'aliado') && (
              <AddressAutocompleteMap
                label={role === 'aliado' ? 'Direccion de bodega' : 'Ubicacion inicial del repartidor'}
                placeholder="Ej: Laureles, Medellin"
                value={address}
                latitude={latitude}
                longitude={longitude}
                onAddressChange={(nextAddress) => {
                  setAddress(nextAddress);
                  setLatitude('');
                  setLongitude('');
                }}
                onLocationChange={({ lat, lng }) => {
                  setLatitude(lat);
                  setLongitude(lng);
                }}
              />
            )}

            {role === 'driver' && (
              <div className="form-row">
                <div className="form-group">
                  <label>Telefono</label>
                  <input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="3001234567" />
                </div>
                <div className="form-group">
                  <label>Capacidad kg</label>
                  <input value={capacity} onChange={(event) => setCapacity(event.target.value)} placeholder="15" />
                </div>
              </div>
            )}

            <button type="submit" className="btn-primary mt-4">
              Crear Usuario
            </button>
          </form>
        </section>

        <section className="panel">
          <h2>Usuarios Registrados <span className="count">{users.length}</span></h2>
          <div className="list-container">
            {users.map((user) => (
              <div key={user.id} className="card">
                <div className="card-info">
                  <h3>{user.name}</h3>
                  <p>@{user.username}</p>
                </div>
                <div className={`badge ${user.role === 'admin' ? 'en-ruta' : 'disponible'}`}>
                  {user.role === 'admin' ? 'Admin' : user.role === 'aliado' ? 'Aliado' : 'Repartidor'}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
