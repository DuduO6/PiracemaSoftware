import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/motoristas.css";

function Motoristas() {
  const [motoristas, setMotoristas] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .get("/api/motoristas/")
      .then((res) => setMotoristas(res.data))
      .catch((err) => console.error("Erro ao carregar motoristas:", err));
  }, []);

  return (
    <div className="motoristas-container">

      <h1 className="titulo">MOTORISTAS</h1>

      <div className="btn-row">
        <button
          className="white-btn"
          onClick={() => navigate("/motoristas/novo")}
        >
          NOVO
        </button>

        <button
          className="white-btn"
          onClick={() => alert("Selecione um motorista para editar")}
        >
          EDITAR
        </button>

        <button
          className="white-btn"
          onClick={() => alert("Selecione um motorista para remover")}
        >
          REMOVER
        </button>
      </div>

      <div className="cards-grid">
        {motoristas.map((m) => (
          <div key={m.id} className="motorista-card">

            <h2 className="motorista-nome">{m.nome}</h2>

            <p><strong>CPF:</strong> {m.cpf}</p>
            <p><strong>Idade:</strong> {m.idade}</p>
            <p><strong>Venc. CNH:</strong> {m.venc_cnh}</p>

            <p>
              <strong>Caminhão:</strong>{" "}
              {m.caminhao ? m.caminhao : "—"}
            </p>

            <button
              className="info-link"
              onClick={() => navigate(`/motoristas/${m.id}`)}
            >
              Informações
            </button>

          </div>
        ))}
      </div>
    </div>
  );
}

export default Motoristas;
