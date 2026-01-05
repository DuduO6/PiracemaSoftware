import React, { useState } from "react";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import { logout } from '../services/auth';

import "../styles/layout.css";
import logo from "../assets/logo.svg";


function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const toggleSidebar = () => setSidebarOpen(prev => !prev);
  const closeSidebar = () => setSidebarOpen(false);

  const handleMenuClick = (item, path) => {
    navigate(path);
    if (window.innerWidth <= 768) closeSidebar();
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <div className="layout-wrapper">
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
          <button className="close-btn" onClick={closeSidebar} aria-label="Fechar menu">
            ✖
          </button>
        </div>

        <ul className="menu-list">
          <li>
            <button 
              className={`menu-btn ${isActive("/home") ? "active" : ""}`} 
              onClick={() => handleMenuClick("HOME", "/home")}
            >
              HOME
            </button>
          </li>
          <li>
            <button 
              className={`menu-btn ${isActive("/motoristas") ? "active" : ""}`} 
              onClick={() => handleMenuClick("MOTORISTAS", "/motoristas")}
            >
              MOTORISTAS
            </button>
          </li>
          <li>
            <button 
              className={`menu-btn ${
                isActive("/caminhoes") || location.pathname.startsWith("/caminhoes/")
                  ? "active"
                  : ""
              }`} 
              onClick={() => handleMenuClick("VEÍCULOS", "/caminhoes")}
            >
              VEÍCULOS
            </button>
          </li>
          <li>
            <button 
              className={`menu-btn ${isActive("/viagens") ? "active" : ""}`} 
              onClick={() => handleMenuClick("VIAGENS", "/viagens")}
            >
              VIAGENS
            </button>
          </li>
          <li>
            <button 
              className={`menu-btn ${isActive("/despesas") ? "active" : ""}`} 
              onClick={() => handleMenuClick("DESPESAS", "/despesas")}
            >
              DESPESAS
            </button>
          </li>

          <li>
            <button 
              className={`menu-btn ${isActive("/acertos") ? "active" : ""}`} 
              onClick={() => handleMenuClick("ACERTOS", "/acertos")}
            >
              ACERTOS
            </button>
          </li>

          <hr className="divider" />

          <li>
            <button 
              className={`menu-btn ${isActive("/suporte") ? "active" : ""}`} 
              onClick={() => handleMenuClick("SUPORTE", "/suporte")}
            >
              SUPORTE
            </button>
          </li>

          <li>
            <button 
              className="menu-btn logout-btn" 
              onClick={handleLogout}
            >
              SAIR
            </button>
          </li>
        </ul>
      </aside>

      <main className={`main-content ${sidebarOpen ? "sidebar-open" : ""}`}>
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;