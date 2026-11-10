import React, { useState } from 'react';
import { useNavigate, Link } from "react-router-dom";
import api from "../api/api";
import '../styles/auth.css';
import ThemeControl from './ThemeControl';
import UiIcon from './UiIcon';

function Login() {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });

  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
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

    setIsSubmitting(true);

    try {
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
    } finally {
      setIsSubmitting(false);
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
      <div className="auth-theme-control">
        <ThemeControl compact />
      </div>

      <main className="auth-shell">
        <section className="auth-card" aria-labelledby="login-title">
          <header className="auth-card-header">
            <h1 id="login-title">Entre na sua conta</h1>
          </header>

          <form onSubmit={handleSubmit} className="auth-card-form" noValidate>
            <div className="auth-field-group">
              <div className={`auth-input-field ${errors.username ? 'has-error' : ''}`}>
                <input
                  id="login-username"
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder=" "
                  autoComplete="username"
                  aria-invalid={Boolean(errors.username)}
                  aria-describedby={errors.username ? 'login-username-error' : undefined}
                  required
                />
                <label htmlFor="login-username">Nome de usuário ou e-mail</label>
              </div>
              {errors.username && (
                <span id="login-username-error" className="auth-error-message">{errors.username}</span>
              )}
            </div>

            <div className="auth-field-group">
              <div className={`auth-input-field has-password-action ${errors.password ? 'has-error' : ''}`}>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder=" "
                  autoComplete="current-password"
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? 'login-password-error' : undefined}
                  required
                />
                <label htmlFor="login-password">Senha</label>
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword((current) => !current)}
                  aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  title={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  <UiIcon name="eye" size={19} />
                </button>
              </div>
              {errors.password && (
                <span id="login-password-error" className="auth-error-message">{errors.password}</span>
              )}
            </div>

            <div className="auth-actions">
              <button type="submit" className="auth-submit" disabled={isSubmitting}>
                {isSubmitting ? 'ENTRANDO…' : 'ENTRAR'}
              </button>
              <p>
                Ainda não possui uma conta?
                <Link to="/register">Criar conta</Link>
              </p>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}

export default Login;
