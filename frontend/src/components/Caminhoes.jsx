import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/caminhoes.css";

function Caminhoes() {
  const [caminhoes, setCaminhoes] = useState([]);
  const navigate = useNavigate();
  const [editarMode, setEditarMode] = useState(false);


  useEffect(() => {
    api.get("/api/caminhoes/")
      .then(res => setCaminhoes(res.data))
      .catch(err => console.error("Erro ao carregar caminhões:", err));
  }, []);

  return (
    <div className="caminhoes-container">

      <h1 className="titulo">CAMINHÕES</h1>

      <div className="btn-row">
        <button className="white-btn" onClick={() => navigate("/caminhoes/novo")}>
          NOVO
        </button>

        <button className="white-btn" onClick={() => setEditarMode(!editarMode)}>
        {editarMode ? "CANCELAR" : "EDITAR"}
        </button>

        <button className="white-btn" onClick={() => alert("Selecione um caminhão para remover")}>
          REMOVER
        </button>
      </div>

      <div className="cards-grid">
        {caminhoes.map((c) => (
          <div key={c.id} className="caminhao-card">
            {editarMode && (
            <span 
                className="edit-icon"
                onClick={() => navigate(`/caminhoes/editar/${c.id}`)}
            >
                📝
            </span>
            )}

            <h2 className="caminhao-nome">{c.nome_conjunto}</h2>
            <p><strong>Placa cavalo:</strong> {c.placa_cavalo}</p>
            <p><strong>Total de placas:</strong> {c.qtd_placas}</p>
            <p><strong>Carretas:</strong> {c.carretas.length}</p>

            <button 
              className="info-link"
              onClick={() => navigate(`/caminhoes/${c.id}`)}
            >
              Informações
            </button>

          </div>
        ))}
      </div>

    </div>
  );
}

export default Caminhoes;
