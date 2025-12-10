import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/motoristaDetalhes.css";

function MotoristaDetalhes() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [motorista, setMotorista] = useState(null);
  const [caminhao, setCaminhao] = useState(null);
  const [vales, setVales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editandoVale, setEditandoVale] = useState(null);
  const [valeEditData, setValeEditData] = useState({});

  useEffect(() => {
    carregarDados();
  }, [id]);

  const carregarDados = () => {
    api.get(`/api/motoristas/${id}/`)
      .then(res => {
        setMotorista(res.data);
        
        if (res.data.caminhao) {
          return api.get(`/api/caminhoes/${res.data.caminhao}/`);
        }
        return null;
      })
      .then(caminhaoRes => {
        if (caminhaoRes) {
          setCaminhao(caminhaoRes.data);
        }
        return api.get(`/api/vales/?motorista=${id}`);
      })
      .then(valesRes => {
        setVales(valesRes.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Erro ao carregar dados:", err);
        setLoading(false);
      });
  };

  const handleTogglePago = async (vale) => {
    try {
      await api.patch(`/api/vales/${vale.id}/`, {
        pago: !vale.pago
      });
      
      setVales(vales.map(v => 
        v.id === vale.id ? { ...v, pago: !v.pago } : v
      ));

    } catch (err) {
      console.error("Erro ao atualizar vale:", err);
      alert("Erro ao atualizar status do vale");
    }
  };

  const handleEditarVale = (vale) => {
    setEditandoVale(vale.id);
    setValeEditData({
      valor: vale.valor,
      descricao: vale.descricao || '',
      data: vale.data
    });
  };

  const handleSalvarEdicao = async (valeId) => {
    if (!valeEditData.valor || parseFloat(valeEditData.valor) <= 0) {
      alert("Informe um valor válido!");
      return;
    }

    try {
      await api.patch(`/api/vales/${valeId}/`, {
        valor: parseFloat(valeEditData.valor),
        descricao: valeEditData.descricao,
        data: valeEditData.data
      });

      setVales(vales.map(v => 
        v.id === valeId ? { ...v, ...valeEditData, valor: parseFloat(valeEditData.valor) } : v
      ));
      
      setEditandoVale(null);
      setValeEditData({});
      alert("Vale atualizado com sucesso!");

    } catch (err) {
      console.error("Erro ao editar vale:", err);
      alert("Erro ao editar vale");
    }
  };

  const handleCancelarEdicao = () => {
    setEditandoVale(null);
    setValeEditData({});
  };

  const handleRemoverVale = async (valeId) => {
    const confirmar = window.confirm("Tem certeza que deseja remover este vale?");
    if (!confirmar) return;

    try {
      await api.delete(`/api/vales/${valeId}/`);
      setVales(vales.filter(v => v.id !== valeId));
      alert("Vale removido com sucesso!");
    } catch (err) {
      console.error("Erro ao remover vale:", err);
      alert("Erro ao remover vale");
    }
  };

  const calcularTotalVales = () => {
    return vales
      .filter(v => !v.pago)
      .reduce((total, vale) => total + parseFloat(vale.valor), 0);
  };

  if (loading) {
    return (
      <div className="detalhes-container">
        <h1 className="titulo">Carregando...</h1>
      </div>
    );
  }

  if (!motorista) {
    return (
      <div className="detalhes-container">
        <h1 className="titulo">Motorista não encontrado</h1>
        <button className="white-btn" onClick={() => navigate("/motoristas")}>
          VOLTAR
        </button>
      </div>
    );
  }

  return (
    <div className="detalhes-container">
      <h1 className="titulo">INFORMAÇÕES DO MOTORISTA</h1>

      <button className="white-btn voltar-btn" onClick={() => navigate("/motoristas")}>
        VOLTAR
      </button>

      <div className="info-card">
        <h2 className="card-titulo">{motorista.nome}</h2>
        
        <div className="info-section">
          <h3 className="section-titulo">Dados Pessoais</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">CPF:</span>
              <span className="info-value">{motorista.cpf}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Idade:</span>
              <span className="info-value">{motorista.idade} anos</span>
            </div>
          </div>
        </div>

        <div className="info-section">
          <h3 className="section-titulo">Habilitação</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Vencimento CNH:</span>
              <span className="info-value">
                {motorista.venc_cnh ? new Date(motorista.venc_cnh).toLocaleDateString('pt-BR') : '—'}
              </span>
            </div>
          </div>
        </div>

        <div className="info-section">
          <h3 className="section-titulo">Vales Pendentes</h3>
          <div className="vales-resumo">
            <p className="total-vales">
              Total a Pagar: <strong>R$ {calcularTotalVales().toFixed(2)}</strong>
            </p>
          </div>
        </div>

        <div className="info-section">
          <h3 className="section-titulo">Conjunto Vinculado</h3>
          {caminhao ? (
            <div className="caminhao-vinculado">
              <div className="caminhao-header">
                <div className="caminhao-nome-destaque">{caminhao.nome_conjunto}</div>
              </div>
              
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">Placa do Cavalo:</span>
                  <span className="info-value">{caminhao.placa_cavalo}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Total de Placas:</span>
                  <span className="info-value">{caminhao.qtd_placas}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Número de Carretas:</span>
                  <span className="info-value">{caminhao.carretas?.length || 0}</span>
                </div>
              </div>

              {caminhao.carretas && caminhao.carretas.length > 0 && (
                <div className="carretas-resumo">
                  <h4 className="carretas-titulo">Carretas</h4>
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
                          {carreta.renavam && (
                            <div className="info-item">
                              <span className="info-label">RENAVAM:</span>
                              <span className="info-value">{carreta.renavam}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="no-caminhao">Nenhum conjunto vinculado</p>
          )}
        </div>

        <div className="info-section">
          <h3 className="section-titulo">Histórico de Vales</h3>
          {vales.length > 0 ? (
            <div className="vales-table-container">
              <table className="vales-table">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Descrição</th>
                    <th>Valor</th>
                    <th>Pago</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {vales.map((vale) => (
                    <tr key={vale.id} className={vale.pago ? 'vale-pago' : ''}>
                      {editandoVale === vale.id ? (
                        <>
                          <td>
                            <input
                              type="date"
                              value={valeEditData.data}
                              onChange={(e) => setValeEditData({...valeEditData, data: e.target.value})}
                              className="edit-input"
                            />
                          </td>
                          <td>
                            <input
                              type="text"
                              value={valeEditData.descricao}
                              onChange={(e) => setValeEditData({...valeEditData, descricao: e.target.value})}
                              className="edit-input"
                              placeholder="Descrição"
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              step="0.01"
                              value={valeEditData.valor}
                              onChange={(e) => setValeEditData({...valeEditData, valor: e.target.value})}
                              className="edit-input"
                            />
                          </td>
                          <td>
                            <input
                              type="checkbox"
                              checked={vale.pago}
                              disabled
                              className="checkbox-pago"
                            />
                          </td>
                          <td>
                            <div className="acoes-buttons">
                              <button 
                                className="btn-salvar-mini"
                                onClick={() => handleSalvarEdicao(vale.id)}
                              >
                                ✓
                              </button>
                              <button 
                                className="btn-cancelar-mini"
                                onClick={handleCancelarEdicao}
                              >
                                ✕
                              </button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td>{new Date(vale.data).toLocaleDateString('pt-BR')}</td>
                          <td>{vale.descricao || '—'}</td>
                          <td>R$ {parseFloat(vale.valor).toFixed(2)}</td>
                          <td>
                            <input
                              type="checkbox"
                              checked={vale.pago}
                              onChange={() => handleTogglePago(vale)}
                              className="checkbox-pago"
                            />
                          </td>
                          <td>
                            <div className="acoes-buttons">
                              <button 
                                className="btn-editar-mini"
                                onClick={() => handleEditarVale(vale)}
                              >
                                ✎
                              </button>
                              <button 
                                className="btn-remover-mini"
                                onClick={() => handleRemoverVale(vale.id)}
                              >
                                🗑
                              </button>
                            </div>
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="no-vales">Nenhum vale registrado</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default MotoristaDetalhes;