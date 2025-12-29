import React, { useEffect, useState } from "react";
import api from "../api/api";
import "../styles/acertos.css";

const Acertos = () => {
  const [acertos, setAcertos] = useState([]);
  const [acertoSelecionado, setAcertoSelecionado] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    carregarAcertos();
  }, []);

  const carregarAcertos = () => {
    api.get("/api/acertos/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || [];
        setAcertos(data);
      })
      .catch((err) => console.error("Erro ao carregar acertos:", err));
  };

  const visualizarAcerto = (id) => {
    api.get(`/api/acertos/${id}/`)
      .then((res) => {
        setAcertoSelecionado(res.data);
        setShowModal(true);
      })
      .catch((err) => console.error("Erro ao carregar detalhes:", err));
  };

  const fecharModal = () => {
    setShowModal(false);
    setAcertoSelecionado(null);
  };

  const formatarData = (dataStr) => {
    const [ano, mes, dia] = dataStr.split('-');
    return `${dia}/${mes}/${ano}`;
  };

  const formatarDataHora = (dataStr) => {
    const data = new Date(dataStr);
    return data.toLocaleString('pt-BR');
  };

  return (
    <div className="acertos-container">
      <h1 className="titulo">HISTÓRICO DE ACERTOS</h1>

      <div className="info-acertos">
        <p className="total-text">TOTAL DE ACERTOS: {acertos.length}</p>
      </div>

      <div className="table-wrapper">
        <table className="acertos-table">
          <thead>
            <tr>
              <th>DATA GERAÇÃO</th>
              <th>MOTORISTA</th>
              <th>PERÍODO</th>
              <th>VIAGENS</th>
              <th>VALOR A RECEBER</th>
              <th>AÇÕES</th>
            </tr>
          </thead>
          <tbody>
            {acertos.map((acerto) => (
              <tr key={acerto.id}>
                <td>{formatarDataHora(acerto.data_geracao)}</td>
                <td>{acerto.motorista_nome}</td>
                <td>
                  {formatarData(acerto.data_inicio)} até {formatarData(acerto.data_fim)}
                </td>
                <td>{acerto.total_viagens}</td>
                <td>R$ {Number(acerto.valor_a_receber).toFixed(2)}</td>
                <td>
                  <button
                    className="btn-visualizar"
                    onClick={() => visualizarAcerto(acerto.id)}
                  >
                    VISUALIZAR
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal de Detalhes */}
      {showModal && acertoSelecionado && (
        <div className="modal-overlay" onClick={fecharModal}>
          <div className="modal-acerto-detalhes" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Detalhes do Acerto</h2>
              <button className="btn-fechar" onClick={fecharModal}>✕</button>
            </div>

            <div className="acerto-info-box">
              <div className="info-row">
                <strong>Motorista:</strong> {acertoSelecionado.motorista_nome}
              </div>
              <div className="info-row">
                <strong>Período:</strong> {formatarData(acertoSelecionado.data_inicio)} até {formatarData(acertoSelecionado.data_fim)}
              </div>
              <div className="info-row">
                <strong>Data de Geração:</strong> {formatarDataHora(acertoSelecionado.data_geracao)}
              </div>
            </div>

            <div className="acerto-section">
              <h3>Viagens ({acertoSelecionado.total_viagens})</h3>
              <div className="table-wrapper-modal">
                <table className="tabela-modal">
                  <thead>
                    <tr>
                      <th>DATA</th>
                      <th>ORIGEM</th>
                      <th>DESTINO</th>
                      <th>CLIENTE</th>
                      <th>PESO</th>
                      <th>R$/TN</th>
                      <th>VALOR</th>
                      <th>PAGO</th>
                    </tr>
                  </thead>
                  <tbody>
                    {acertoSelecionado.itens.map((item) => (
                      <tr key={item.id}>
                        <td>{formatarData(item.data)}</td>
                        <td>{item.origem}</td>
                        <td>{item.destino}</td>
                        <td>{item.cliente}</td>
                        <td>{item.peso}</td>
                        <td>R$ {Number(item.valor_tonelada).toFixed(2)}</td>
                        <td>R$ {Number(item.valor_total).toFixed(2)}</td>
                        <td>
                          <span className={`status-badge ${item.pago ? 'status-pago' : 'status-pendente'}`}>
                            {item.pago ? "SIM" : "NÃO"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {acertoSelecionado.vales.length > 0 && (
              <div className="acerto-section">
                <h3>Vales não pagos ({acertoSelecionado.vales.length})</h3>
                <div className="table-wrapper-modal">
                  <table className="tabela-modal">
                    <thead>
                      <tr>
                        <th>DATA</th>
                        <th>VALOR</th>
                      </tr>
                    </thead>
                    <tbody>
                      {acertoSelecionado.vales.map((vale) => (
                        <tr key={vale.id}>
                          <td>{formatarData(vale.data)}</td>
                          <td>R$ {Number(vale.valor).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="acerto-resumo">
              <div className="resumo-item">
                <span>Valor Total das Viagens:</span>
                <strong>R$ {Number(acertoSelecionado.valor_total_viagens).toFixed(2)}</strong>
              </div>
              <div className="resumo-item">
                <span>Total de Vales:</span>
                <strong>R$ {Number(acertoSelecionado.total_vales).toFixed(2)}</strong>
              </div>
              <div className="resumo-item">
                <span>Comissão (13%):</span>
                <strong>R$ {Number(acertoSelecionado.comissao).toFixed(2)}</strong>
              </div>
              <div className="resumo-item destaque">
                <span>Valor a Receber:</span>
                <strong>R$ {Number(acertoSelecionado.valor_a_receber).toFixed(2)}</strong>
              </div>
            </div>

            <div className="modal-buttons">
              <button className="btn-cancelar" onClick={fecharModal}>
                FECHAR
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Acertos;