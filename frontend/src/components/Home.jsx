import React, { useState, useEffect } from "react";
import "../styles/home.css";
import api from "../api/api";

function Home() {
  const [dashboardData, setDashboardData] = useState({
    faturamento: 0,
    despesas: 0,
    lucro: 0
  });

  // 🔥 CARREGAR DADOS DA API
  useEffect(() => {
    const token = localStorage.getItem("access");

    if (!token) {
      window.location.href = "/";
      return;
    }

    api.get("/api/", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then(res => {
        setDashboardData(res.data);
      })
      .catch(err => {
        console.error("Erro carregando API:", err);

        // token expirado -> tentar renovar
        if (err.response?.status === 401 || err.response?.status === 403) {
          window.location.href = "/";
        }
      });
  }, []);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Home</h1>
        <div className="user-info">
          <span>Olá, usuário</span>
        </div>
      </header>

      {/* 🔥 AGORA OS VALORES SÃO REAIS */}
      <section className="cards-row">
        <div className="info-block">
          <h2>FATURAMENTO (MÊS)</h2>
          <p className="value">R$ {dashboardData.faturamento.toLocaleString("pt-BR")}</p>
        </div>

        <div className="info-block">
          <h2>DESPESAS</h2>
          <p className="value">R$ {dashboardData.despesas.toLocaleString("pt-BR")}</p>
        </div>

        <div className="info-block">
          <h2>LUCRO</h2>
          <p className="value">R$ {dashboardData.lucro.toLocaleString("pt-BR")}</p>
        </div>
      </section>

      <section className="content-area">
        <h3>FATURAMENTO</h3>
        <p>Aqui aparecerão os detalhes de <strong>FATURAMENTO</strong>.</p>
      </section>
    </div>
  );
}

export default Home;