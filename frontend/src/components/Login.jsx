import React, { useState } from 'react';
import { useNavigate, Link } from "react-router-dom";
import api from '../api'; // ← ADICIONE ESTA LINHA
import '../styles/auth.css';
import logo from '../assets/logo.svg';

function Login() {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });

  const [errors, setErrors] = useState({});
  const navigate = useNavigate();

  const validateForm = () => {
    const newErrors = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Nome/E-mail é obrigatório';
    }

    if (!formData.password) {
      newErrors.password = 'Senha é obrigatória';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    try {
      // ← SUBSTITUA O FETCH POR API
      const response = await api.post('/auth/login/', {
        username: formData.username,
        password: formData.password
      });

      const data = response.data;

      // Salva tokens vindos do backend Django
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);

      navigate("/home", { replace: true });
      
    } catch (error) {
      console.error('Erro:', error);
      if (error.response?.data?.error) {
        alert(error.response.data.error);
      } else {
        alert('Erro ao conectar com o servidor');
      }
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;

    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  return (
    <div className="auth-container">
      <div className="logo-section">
        <div className="logo-wrapper">
          <img src={logo} alt="Piracema Logo" className="logo-monitor" />
        </div>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label>Nome/E-mail:</label>
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleChange}
            className={`form-input ${errors.username ? 'input-error' : ''}`}
          />
          {errors.username && <span className="error-message">{errors.username}</span>}
        </div>

        <div className="form-group">
          <label>Senha:</label>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            className={`form-input ${errors.password ? 'input-error' : ''}`}
          />
          {errors.password && <span className="error-message">{errors.password}</span>}
        </div>

        <button type="submit" className="btn-submit">ENTRAR</button>

        <div className="register-link">
          <p>NÃO POSSUI UMA CONTA?</p>
          <Link to="/register">REGISTRE-SE</Link>
        </div>
      </form>
    </div>
  );
}

export default Login;