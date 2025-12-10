import React, { useState, useEffect } from "react";
import "../styles/home.css";
import api from "../api/api";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

function Home() {
  const [data, setData] = useState({
    faturamento: 0,
    viagens: 0,
    ranking_motoristas: [],
    total_vales_pendentes: 0,
    motoristas_devendo: []
  });

  const [username, setUsername] = useState("");
  const [dias, setDias] = useState(30);
  const [dropdown, setDropdown] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access");

    if (!token) {
      window.location.href = "/";
      return;
    }

    api.get(`/api/?dias=${dias}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => setData(res.data))
      .catch(err => console.error("Erro carregando dashboard", err));

    api.get("/auth/user/", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => setUsername(res.data.username))
      .catch(() => setUsername("Usuário"));
  }, [dias]);

  const chartData = {
    labels: data.ranking_motoristas.map(item => item.motorista__nome),
    datasets: [
      {
        label: `Viagens (${dias} dias)`,
        data: data.ranking_motoristas.map(item => item.total),
        backgroundColor: ["#4F46E5", "#EF4444", "#818CF8", "#A5B4FC", "#C7D2FE"],
        borderColor: "#1E1E1E",
        borderWidth: 1,
        barThickness: 140
      }
    ]
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Home</h1>
        <div className="user-info">Olá, {username}</div>
      </header>

      {/* Seleção de dias - MANTENDO PADRÃO */}
      <section className="periodo-container">
        <label>Período:</label>
        <div className="periodo-input-wrapper">
          <input
            type="number"
            min="1"
            value={dias}
            onChange={e => setDias(Number(e.target.value))}
            className="periodo-input"
          />

          <button className="periodo-btn" onClick={() => setDropdown(!dropdown)}>
            ▼
          </button>

          {dropdown && (
            <div className="periodo-dropdown">
              {[7, 15, 30, 50, 90].map(v => (
                <div
                  key={v}
                  className="dropdown-option"
                  onClick={() => {
                    setDias(v);
                    setDropdown(false);
                  }}
                >
                  {v} dias
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* CARDS */}
      <section className="cards-row">
        <div className="info-block">
          <h2>Faturamento ({dias} dias)</h2>
          <p className="value">R$ {data.faturamento.toLocaleString("pt-BR")}</p>
        </div>

        <div className="info-block">
          <h2>Viagens ({dias} dias)</h2>
          <p className="value">{data.viagens}</p>
        </div>

        <div className="info-block warning">
          <h2>Vales não pagos</h2>
          <p className="value red">
            R$ {data.total_vales_pendentes.toLocaleString("pt-BR")}
          </p>
        </div>
      </section>

      {/* Gráfico */}
      <section className="content-area">
        <h3>Motoristas com mais viagens ({dias} dias)</h3>
        <Bar data={chartData} />
      </section>

      {/* Tabela */}
      <section className="content-area">
        <h3>Detalhamento dos vales não pagos</h3>

        {data.motoristas_devendo.length === 0 ? (
          <p>Nenhum vale pendente.</p>
        ) : (
          <table className="vales-table">
            <thead>
              <tr>
                <th>Motorista</th>
                <th>Total devido</th>
              </tr>
            </thead>
            <tbody>
              {data.motoristas_devendo.map((item, index) => (
                <tr key={index}>
                  <td>{item.motorista__nome}</td>
                  <td>R$ {item.total.toLocaleString("pt-BR")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default Home;
