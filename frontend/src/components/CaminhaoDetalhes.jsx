import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/caminhaoDetalhes.css";

function CaminhaoDetalhes() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [caminhao, setCaminhao] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/api/caminhoes/${id}/`)
      .then(res => {
        setCaminhao(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Erro ao carregar caminhão:", err);
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="detalhes-container">
        <h1 className="titulo">Carregando...</h1>
      </div>
    );
  }

  if (!caminhao) {
    return (
      <div className="detalhes-container">
        <h1 className="titulo">Caminhão não encontrado</h1>
        <button className="white-btn" onClick={() => navigate("/caminhoes")}>
          VOLTAR
        </button>
      </div>
    );
  }

  return (
    <div className="detalhes-container">
      <h1 className="titulo">INFORMAÇÕES DO CAMINHÃO</h1>

      <button className="white-btn voltar-btn" onClick={() => navigate("/caminhoes")}>
        VOLTAR
      </button>

      <div className="info-card">
        <h2 className="card-titulo">{caminhao.nome_conjunto}</h2>
        
        <div className="info-section">
          <h3 className="section-titulo">Dados do Cavalo</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Placa do Cavalo:</span>
              <span className="info-value">{caminhao.placa_cavalo}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Total de Placas:</span>
              <span className="info-value">{caminhao.qtd_placas}</span>
            </div>
          </div>
        </div>

        {caminhao.carretas && caminhao.carretas.length > 0 && (
          <div className="info-section">
            <h3 className="section-titulo">Carretas ({caminhao.carretas.length})</h3>
            <div className="carretas-list">
              {caminhao.carretas.map((carreta, index) => (
                <div key={carreta.id || index} className="carreta-item">
                  <div className="carreta-numero">Carreta {index + 1}</div>
                  <div className="info-grid">
                    {carreta.placa && (
                      <div className="info-item">
                        <span className="info-label">Placa:</span>
                        <span className="info-value">{carreta.placa}</span>
                      </div>
                    )}
                    {carreta.tipo && (
                      <div className="info-item">
                        <span className="info-label">Tipo:</span>
                        <span className="info-value">{carreta.tipo}</span>
                      </div>
                    )}
                    {carreta.capacidade && (
                      <div className="info-item">
                        <span className="info-label">Capacidade:</span>
                        <span className="info-value">{carreta.capacidade}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(!caminhao.carretas || caminhao.carretas.length === 0) && (
          <div className="info-section">
            <h3 className="section-titulo">Carretas</h3>
            <p className="no-carretas">Nenhuma carreta cadastrada</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default CaminhaoDetalhes;