import { useState } from 'react';
import { useAppContext } from '../../context/AppContext';

export const ManageUsers = () => {
  const { users, addUser } = useAppContext();
  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('driver');
  const [successMsg, setSuccessMsg] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    await addUser({ nombre: name, username, password, role });
    setName('');
    setUsername('');
    setPassword('');
    setSuccessMsg('Usuario creado exitosamente');
    setTimeout(() => setSuccessMsg(''), 3000);
  };

  return (
    <div className="dashboard-content">
      <header className="page-header">
        <h1>Gestión de Usuarios</h1>
        <p>Administra y registra nuevos roles en la plataforma.</p>
      </header>

      <div className="main-grid">
        <section className="panel form-panel">
          <h2>Crear Nuevo Usuario</h2>
          <form onSubmit={handleSubmit} className="custom-form">
            {successMsg && <div className="success-message">{successMsg}</div>}
            
            <div className="form-group">
              <label>Nombre Completo</label>
              <input 
                type="text" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                required 
              />
            </div>

            <div className="form-group">
              <label>Usuario (Login)</label>
              <input 
                type="text" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                required 
              />
            </div>

            <div className="form-group">
              <label>Contraseña</label>
              <input 
                type="password" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required 
              />
            </div>

            <div className="form-group">
              <label>Rol</label>
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="driver">Repartidor</option>
                <option value="admin">Administrador</option>
              </select>
            </div>

            <button type="submit" className="btn-primary mt-4">
              ➕ Crear Usuario
            </button>
          </form>
        </section>

        <section className="panel">
          <h2>Usuarios Registrados <span className="count">{users.length}</span></h2>
          <div className="list-container">
            {users.map(u => (
              <div key={u.id} className="card">
                <div className="card-info">
                  <h3>{u.name}</h3>
                  <p>@{u.username}</p>
                </div>
                <div className={`badge ${u.role === 'admin' ? 'en-ruta' : 'disponible'}`}>
                  {u.role === 'admin' ? 'Admin' : 'Repartidor'}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
