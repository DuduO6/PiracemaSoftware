import React, { useState, useEffect } from "react";
import "../styles/home.css";
import api from "../api/api";
import { Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  LineElement,
  PointElement
} from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend, LineElement, PointElement);

function Home() {
  const [data, setData] = useState({
    faturamento: 0,
    viagens: 0,
    ranking_motoristas: [],
    total_vales_pendentes: 0,
    motoristas_devendo: [],
    evolucao_diaria: []
  });

  const [username, setUsername] = useState("");
  const [dias, setDias] = useState(30);
  const [dropdown, setDropdown] = useState(false);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState("grid"); // grid ou list

  useEffect(() => {
    const token = localStorage.getItem("access");

    if (!token) {
      window.location.href = "/";
      return;
    }

    setLoading(true);

    Promise.all([
      api.get(`/api/?dias=${dias}`, {
        headers: { Authorization: `Bearer ${token}` }
      }),
      api.get("/auth/user/", {
        headers: { Authorization: `Bearer ${token}` }
      })
    ])
      .then(([dashRes, userRes]) => {
        setData(dashRes.data);
        setUsername(userRes.data.username);
      })
      .catch(err => console.error("Erro carregando dashboard", err))
      .finally(() => setLoading(false));
  }, [dias]);

  const chartData = {
    labels: data.ranking_motoristas.map(item => item.motorista__nome),
    datasets: [
      {
        label: `Viagens (${dias} dias)`,
        data: data.ranking_motoristas.map(item => item.total),
        backgroundColor: ["#6366F1", "#8B5CF6", "#A78BFA", "#C4B5FD", "#DDD6FE"],
        borderColor: "#1E1E1E",
        borderWidth: 1,
        borderRadius: 8,
        barThickness: 60
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: "rgba(17, 24, 39, 0.95)",
        padding: 12,
        borderColor: "rgba(99, 102, 241, 0.3)",
        borderWidth: 1,
        titleColor: "#E5E7EB",
        bodyColor: "#9CA3AF",
        displayColors: false
      }
    },
    scales: {
      x: {
        grid: { display: false, color: "rgba(255,255,255,0.05)" },
        ticks: { color: "#9CA3AF", font: { size: 11 } }
      },
      y: {
        grid: { color: "rgba(255,255,255,0.05)" },
        ticks: { color: "#9CA3AF", font: { size: 11 } }
      }
    }
  };

  const ticketMedio = data.viagens > 0 ? data.faturamento / data.viagens : 0;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>Dashboard</h1>
          <p className="subtitle">Visão geral do seu negócio</p>
        </div>
        <div className="user-info">
          <div className="avatar">{username.charAt(0).toUpperCase()}</div>
          <span>Olá, {username}</span>
        </div>
      </header>

      {/* Seleção de período com design melhorado */}
      <section className="periodo-container">
        <label>Período de análise:</label>
        <div className="periodo-controls">
          <div className="periodo-input-wrapper">
            <input
              type="number"
              min="1"
              value={dias}
              onChange={e => setDias(Number(e.target.value))}
              className="periodo-input"
            />
            <span className="periodo-label">dias</span>
            <button className="periodo-btn" onClick={() => setDropdown(!dropdown)}>
              ▼
            </button>

            {dropdown && (
              <div className="periodo-dropdown">
                {[7, 15, 30, 50, 90].map(v => (
                  <div
                    key={v}
                    className={`dropdown-option ${dias === v ? "active" : ""}`}
                    onClick={() => {
                      setDias(v);
                      setDropdown(false);
                    }}
                  >
                    <span>{v} dias</span>
                    {dias === v && <span className="check">✓</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Carregando dados...</p>
        </div>
      ) : (
        <>
          {/* CARDS com mais informações */}
          <section className="cards-row">
            <div className="info-block primary">
              <div className="block-icon">💰</div>
              <div className="block-content">
                <h2>Faturamento Total</h2>
                <p className="value">R$ {data.faturamento.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
                <span className="period-label">Últimos {dias} dias</span>
              </div>
            </div>

            <div className="info-block success">
              <div className="block-icon">🚗</div>
              <div className="block-content">
                <h2>Total de Viagens</h2>
                <p className="value">{data.viagens}</p>
                <span className="period-label">Últimos {dias} dias</span>
              </div>
            </div>

            <div className="info-block info">
              <div className="block-icon">📊</div>
              <div className="block-content">
                <h2>Ticket Médio</h2>
                <p className="value">R$ {ticketMedio.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
                <span className="period-label">Por viagem</span>
              </div>
            </div>

            <div className="info-block warning">
              <div className="block-icon">⚠️</div>
              <div className="block-content">
                <h2>Vales Pendentes</h2>
                <p className="value red">
                  R$ {data.total_vales_pendentes.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                </p>
                <span className="period-label">{data.motoristas_devendo.length} motorista(s)</span>
              </div>
            </div>
          </section>

          {/* Gráfico de ranking */}
          <section className="content-area chart-container">
            <div className="section-header">
              <h3>🏆 Ranking de Motoristas</h3>
              <span className="badge">{dias} dias</span>
            </div>
            {data.ranking_motoristas.length > 0 ? (
              <div style={{ height: "320px" }}>
                <Bar data={chartData} options={chartOptions} />
              </div>
            ) : (
              <div className="empty-state">
                <p>Nenhuma viagem registrada no período selecionado.</p>
              </div>
            )}
          </section>

          {/* Tabela de vales com controles */}
          <section className="content-area">
            <div className="section-header">
              <h3>💳 Detalhamento dos Vales Não Pagos</h3>
              <div className="view-controls">
                <button
                  className={`view-btn ${viewMode === "grid" ? "active" : ""}`}
                  onClick={() => setViewMode("grid")}
                  title="Visualização em grade"
                >
                  ⊞
                </button>
                <button
                  className={`view-btn ${viewMode === "list" ? "active" : ""}`}
                  onClick={() => setViewMode("list")}
                  title="Visualização em lista"
                >
                  ☰
                </button>
              </div>
            </div>

            {data.motoristas_devendo.length === 0 ? (
              <div className="empty-state success">
                <div className="empty-icon">✓</div>
                <p>Nenhum vale pendente. Tudo em dia!</p>
              </div>
            ) : viewMode === "list" ? (
              <table className="vales-table">
                <thead>
                  <tr>
                    <th>Motorista</th>
                    <th>Total Devido</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.motoristas_devendo.map((item, index) => (
                    <tr key={index}>
                      <td>
                        <div className="motorista-cell">
                          <div className="avatar-small">{item.motorista__nome.charAt(0)}</div>
                          {item.motorista__nome}
                        </div>
                      </td>
                      <td className="valor-cell">
                        R$ {item.total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </td>
                      <td>
                        <span className="status-badge pending">Pendente</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="vales-grid">
                {data.motoristas_devendo.map((item, index) => (
                  <div key={index} className="vale-card">
                    <div className="vale-header">
                      <div className="avatar-large">{item.motorista__nome.charAt(0)}</div>
                      <div className="vale-info">
                        <h4>{item.motorista__nome}</h4>
                        <span className="status-badge pending">Pendente</span>
                      </div>
                    </div>
                    <div className="vale-footer">
                      <span className="label">Total devido:</span>
                      <span className="valor">
                        R$ {item.total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

export default Home;