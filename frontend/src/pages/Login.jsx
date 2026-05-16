import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../context/AppContext';

export const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, currentUser } = useAppContext();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await login(username, password);
    if (!success) {
      setError('Credenciales inválidas');
    }
  };

  // Si ya hay usuario, redirigir
  if (currentUser) {
    if (currentUser.role === 'admin') navigate('/admin/dashboard');
    else navigate('/driver/dashboard');
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Ruta Fácil</h1>
          <p>Bienvenido de vuelta</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="error-message">{error}</div>}
          
          <div className="form-group">
            <label>Usuario</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ej: admin o carlos"
              required 
            />
          </div>

          <div className="form-group">
            <label>Contraseña</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)}
              placeholder="123"
              required 
            />
          </div>

          <button type="submit" className="btn-primary w-full">
            Ingresar
          </button>
        </form>

        <div className="login-hints">
          <p><strong>Admin:</strong> admin / 123</p>
          <p><strong>Repartidor:</strong> carlos / 123</p>
        </div>
      </div>
    </div>
  );
};
