import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/api";
import { logout } from "../services/auth";
import "../styles/minhaConta.css";


function formatCnpj(value) {
  const normalized = String(value || "").replace(/[^A-Za-z0-9]/g, "").toUpperCase().slice(0, 14);
  if (!/^\d+$/.test(normalized)) return normalized;
  return normalized
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2");
}

function apiError(error) {
  const data = error.response?.data;
  if (data?.cnpj) return Array.isArray(data.cnpj) ? data.cnpj[0] : data.cnpj;
  if (data && typeof data === "object") {
    const first = Object.values(data).flat().find(Boolean);
    if (first) return String(first);
  }
  if (data?.detail) return data.detail;
  return "Não foi possível salvar as alterações.";
}

export default function MinhaConta() {
  const navigate = useNavigate();
  const [account, setAccount] = useState({ username: "", email: "", cnpj: "" });
  const [credentials, setCredentials] = useState({ currentPassword: "", newPassword: "", confirmation: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    api.get("/auth/user/")
      .then(({ data }) => setAccount({ ...data, cnpj: formatCnpj(data.cnpj) }))
      .catch((requestError) => setError(apiError(requestError)))
      .finally(() => setLoading(false));
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const { data } = await api.patch("/auth/user/", {
        username: account.username,
        cnpj: account.cnpj,
        senha_atual: credentials.currentPassword,
        nova_senha: credentials.newPassword,
        confirmar_nova_senha: credentials.confirmation,
      });
      setAccount((current) => ({ ...current, username: data.username, cnpj: formatCnpj(data.cnpj) }));
      setCredentials({ currentPassword: "", newPassword: "", confirmation: "" });
      if (data.senha_alterada) {
        logout();
        alert("Senha alterada. Entre novamente com suas novas credenciais.");
        navigate("/login", { replace: true });
        return;
      }
      setSuccess("Dados da conta atualizados.");
    } catch (requestError) {
      setError(apiError(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="account-page">
      <div className="account-card">
        <header>
          <span>Dados pessoais</span>
          <h1>Minha conta</h1>
          <p>Cadastre o CNPJ associado ao seu acesso. A configuração fiscal do MDF-e continua sendo feita por empresa.</p>
        </header>

        {loading ? <p className="account-loading">Carregando dados…</p> : (
          <form onSubmit={submit}>
            <label>
              Nome de usuário
              <input
                value={account.username}
                onChange={(event) => setAccount((current) => ({ ...current, username: event.target.value }))}
                maxLength={150}
                autoComplete="username"
                required
              />
              <small>Para alterar o nome, informe sua senha atual abaixo.</small>
            </label>
            <label>
              E-mail
              <input value={account.email} disabled />
            </label>
            <label>
              CNPJ
              <input
                value={account.cnpj}
                onChange={(event) => setAccount((current) => ({ ...current, cnpj: formatCnpj(event.target.value) }))}
                placeholder="00.000.000/0000-00"
                maxLength={18}
                autoComplete="organization"
              />
              <small>Deixe vazio para remover. Cada CNPJ pode pertencer a apenas uma conta.</small>
            </label>

            <div className="account-password-section">
              <h2>Segurança</h2>
              <p>A senha atual é obrigatória para trocar o nome de usuário ou definir uma nova senha.</p>
            </div>

            <label>
              Senha atual
              <input
                type="password"
                value={credentials.currentPassword}
                onChange={(event) => setCredentials((current) => ({ ...current, currentPassword: event.target.value }))}
                autoComplete="current-password"
              />
            </label>
            <label>
              Nova senha
              <input
                type="password"
                value={credentials.newPassword}
                onChange={(event) => setCredentials((current) => ({ ...current, newPassword: event.target.value }))}
                autoComplete="new-password"
              />
            </label>
            <label>
              Confirmar nova senha
              <input
                type="password"
                value={credentials.confirmation}
                onChange={(event) => setCredentials((current) => ({ ...current, confirmation: event.target.value }))}
                autoComplete="new-password"
              />
            </label>

            {error && <div className="account-message error" role="alert">{error}</div>}
            {success && <div className="account-message success" role="status">{success}</div>}

            <button type="submit" disabled={saving}>{saving ? "Salvando…" : "Salvar alterações"}</button>
          </form>
        )}
      </div>
    </section>
  );
}
