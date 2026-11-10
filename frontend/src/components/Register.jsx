import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from "../api/api";  
import '../styles/auth.css';
import ThemeControl from './ThemeControl';
import UiIcon from './UiIcon';

function Register() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    cnpj: '',
    password: '',
    confirmPassword: ''
  });

  const [errors, setErrors] = useState({});
  const [showPasswords, setShowPasswords] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const validateForm = () => {
    const newErrors = {};

    if (!formData.username.trim()) {
      newErrors.username = 'O nome de usuário é obrigatório';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'E-mail é obrigatório';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'E-mail inválido';
    }

    if (!formData.password) {
      newErrors.password = 'Senha é obrigatória';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Senha deve ter no mínimo 6 caracteres';
    }

    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'As senhas não coincidem';
    }

    const normalizedCnpj = formData.cnpj.replace(/\D/g, '');
    if (formData.cnpj && normalizedCnpj.length !== 14) {
      newErrors.cnpj = 'CNPJ deve ter 14 números';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsSubmitting(true);

    try {
      await api.post("/auth/register/", {
        username: formData.username,
        email: formData.email,
        cnpj: formData.cnpj,
        password: formData.password
      });

      alert("Cadastro realizado com sucesso!");
      navigate('/login', { replace: true });

    } catch (error) {
      console.error("Erro:", error);
      alert("Erro ao registrar. Confira os dados e tente novamente.");
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

      <main className="auth-shell auth-shell-register">
        <section className="auth-card auth-card-register" aria-labelledby="register-title">
          <header className="auth-card-header">
            <h1 id="register-title">Crie sua conta</h1>
          </header>

          <form onSubmit={handleSubmit} className="auth-card-form" noValidate>
            <div className="auth-register-grid">
              <AuthField
                id="register-username"
                label="Nome de usuário"
                name="username"
                value={formData.username}
                onChange={handleChange}
                error={errors.username}
                autoComplete="username"
                required
              />
              <AuthField
                id="register-email"
                label="E-mail"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                error={errors.email}
                autoComplete="email"
                required
              />
              <AuthField
                id="register-cnpj"
                label="CNPJ (opcional)"
                name="cnpj"
                value={formData.cnpj}
                onChange={handleChange}
                error={errors.cnpj}
                autoComplete="off"
                inputMode="numeric"
                maxLength="18"
              />
              <AuthField
                id="register-password"
                label="Senha"
                name="password"
                type={showPasswords ? 'text' : 'password'}
                value={formData.password}
                onChange={handleChange}
                error={errors.password}
                autoComplete="new-password"
                required
                passwordAction
                showPassword={showPasswords}
                onTogglePassword={() => setShowPasswords((current) => !current)}
              />
              <AuthField
                id="register-confirm-password"
                label="Confirme sua senha"
                name="confirmPassword"
                type={showPasswords ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={handleChange}
                error={errors.confirmPassword}
                autoComplete="new-password"
                required
                passwordAction
                showPassword={showPasswords}
                onTogglePassword={() => setShowPasswords((current) => !current)}
              />
            </div>

            <div className="auth-actions">
              <button type="submit" className="auth-submit" disabled={isSubmitting}>
                {isSubmitting ? 'CADASTRANDO…' : 'CRIAR CONTA'}
              </button>
              <p>
                Já possui uma conta?
                <Link to="/login">Voltar ao login</Link>
              </p>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
}

function AuthField({
  id,
  label,
  error,
  passwordAction = false,
  showPassword = false,
  onTogglePassword,
  ...inputProps
}) {
  const errorId = `${id}-error`;

  return (
    <div className="auth-field-group">
      <div className={`auth-input-field ${passwordAction ? 'has-password-action' : ''} ${error ? 'has-error' : ''}`}>
        <input
          id={id}
          placeholder=" "
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          {...inputProps}
        />
        <label htmlFor={id}>{label}</label>
        {passwordAction && (
          <button
            type="button"
            className="auth-password-toggle"
            onClick={onTogglePassword}
            aria-label={showPassword ? 'Ocultar senhas' : 'Mostrar senhas'}
            title={showPassword ? 'Ocultar senhas' : 'Mostrar senhas'}
          >
            <UiIcon name="eye" size={19} />
          </button>
        )}
      </div>
      {error && <span id={errorId} className="auth-error-message">{error}</span>}
    </div>
  );
}

export default Register;
