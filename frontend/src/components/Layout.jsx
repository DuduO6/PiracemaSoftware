import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { logout } from "../services/auth";
import ThemeControl from "./ThemeControl";
import UiIcon from "./UiIcon";
import "../styles/layout.css";

const menuItems = [
  { label: "Home", path: "/home", icon: "home" },
  { label: "Motoristas", path: "/motoristas", icon: "user" },
  { label: "Veículos", path: "/caminhoes", icon: "truck", prefix: true },
  { label: "Viagens", path: "/viagens", icon: "route" },
  { label: "Manifestos — MDF-e", path: "/manifestos-mdfe", icon: "document" },
  { label: "Despesas", path: "/despesas", icon: "wallet" },
  { label: "Acertos", path: "/acertos", icon: "check" },
  { label: "Seguro de cargas", path: "/seguro-cargas", icon: "shield" },
  { label: "Calculadora de frete", path: "/fretes/calculadora", icon: "calculator" },
];

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 768);
  const navigate = useNavigate();
  const location = useLocation();
  const closeButtonRef = useRef(null);

  const isMobile = () => window.innerWidth <= 768;
  const closeSidebar = () => setSidebarOpen(false);

  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key === "Escape" && sidebarOpen && isMobile()) closeSidebar();
    };
    document.addEventListener("keydown", handleEscape);
    if (sidebarOpen && isMobile()) {
      closeButtonRef.current?.focus();
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [sidebarOpen]);

  const handleMenuClick = (path) => {
    navigate(path);
    if (isMobile()) closeSidebar();
  };

  const isActive = ({ path, prefix }) => (
    prefix ? location.pathname === path || location.pathname.startsWith(`${path}/`) : location.pathname === path
  );

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="layout-wrapper">
      <button
        type="button"
        className={`open-menu-btn ${sidebarOpen ? "hidden-on-desktop" : ""}`}
        onClick={() => setSidebarOpen(true)}
        aria-label="Abrir menu principal"
        aria-expanded={sidebarOpen}
        aria-controls="main-sidebar"
      >
        <UiIcon name="menu" />
      </button>

      <button
        type="button"
        className={`overlay ${sidebarOpen ? "visible" : ""}`}
        onClick={closeSidebar}
        aria-label="Fechar menu principal"
        tabIndex={sidebarOpen ? 0 : -1}
      />

      <aside id="main-sidebar" className={`sidebar ${sidebarOpen ? "open" : ""}`} aria-label="Navegação principal">
        <div className="sidebar-header">
          <div className="sidebar-brand" aria-label="Piracema Software">
            <span className="sidebar-brand-mark"><UiIcon name="truck" size={20} /></span>
            <span>Piracema<small>Software</small></span>
          </div>
          <button ref={closeButtonRef} type="button" className="close-btn" onClick={closeSidebar} aria-label="Recolher menu">
            <UiIcon name="close" size={19} />
          </button>
        </div>

        <nav className="sidebar-nav">
          <ul className="menu-list">
            {menuItems.map((item) => (
              <li key={item.path}>
                <button
                  type="button"
                  className={`menu-btn ${isActive(item) ? "active" : ""}`}
                  onClick={() => handleMenuClick(item.path)}
                  aria-current={isActive(item) ? "page" : undefined}
                  title={item.label}
                >
                  <UiIcon name={item.icon} className="menu-icon" size={19} />
                  <span>{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <ThemeControl />
          <button
            type="button"
            className={`menu-btn ${location.pathname === "/minha-conta" ? "active" : ""}`}
            onClick={() => handleMenuClick("/minha-conta")}
            aria-current={location.pathname === "/minha-conta" ? "page" : undefined}
          >
            <UiIcon name="settings" className="menu-icon" size={19} />
            <span>Minha conta</span>
          </button>
          <button type="button" className="menu-btn logout-btn" onClick={handleLogout}>
            <UiIcon name="logout" className="menu-icon" size={19} />
            <span>Sair</span>
          </button>
        </div>
      </aside>

      <main className={`main-content ${sidebarOpen ? "sidebar-open" : ""}`}>
        <Outlet />
      </main>
    </div>
  );
}
