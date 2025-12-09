import React, { useState, useEffect } from "react";
import "../styles/home.css";
import logo from "../assets/logo.svg";
import api from "../api/api";

function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selected, setSelected] = useState("FATURAMENTO");
  
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

  const toggleSidebar = () => setSidebarOpen(prev => !prev);
  const closeSidebar = () => setSidebarOpen(false);

  const handleMenuClick = (item) => {
    setSelected(item);
    if (window.innerWidth <= 768) closeSidebar();
  };

  return (
    <div className="home-container">

      <button
        className={`open-menu-btn ${sidebarOpen ? "hidden-on-desktop" : ""}`}
        onClick={toggleSidebar}
        aria-label="Abrir menu"
      >
        ☰
      </button>

      <div
        className={`overlay ${sidebarOpen ? "visible" : ""}`}
        onClick={closeSidebar}
        aria-hidden={!sidebarOpen}
      />

      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <img src={logo} alt="Logo" className="sidebar-logo" />
          <button className="close-btn" onClick={closeSidebar} aria-label="Fechar menu">✖</button>
        </div>

        <ul className="menu-list">
          <li><button className={`menu-btn ${selected === "MOTORISTAS" ? "active" : ""}`} onClick={() => handleMenuClick("MOTORISTAS")}>MOTORISTAS</button></li>
          <li><button className={`menu-btn ${selected === "VEÍCULOS" ? "active" : ""}`} onClick={() => handleMenuClick("VEÍCULOS")}>VEÍCULOS</button></li>
          <li><button className={`menu-btn ${selected === "VIAGENS" ? "active" : ""}`} onClick={() => handleMenuClick("VIAGENS")}>VIAGENS</button></li>
          <li><button className={`menu-btn ${selected === "DESPESAS" ? "active" : ""}`} onClick={() => handleMenuClick("DESPESAS")}>DESPESAS</button></li>
          <hr className="divider" />
          <li><button className={`menu-btn ${selected === "SUPORTE" ? "active" : ""}`} onClick={() => handleMenuClick("SUPORTE")}>SUPORTE</button></li>
        </ul>
      </aside>

      <main className="dashboard">
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
          <h3>{selected}</h3>
          <p>Aqui aparecerão os detalhes de <strong>{selected}</strong>.</p>
        </section>

      </main>
    </div>
  );
}

export default Home;
