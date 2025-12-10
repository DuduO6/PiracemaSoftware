import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import "../styles/motoristas.css";

function Motoristas() {
  const [motoristas, setMotoristas] = useState([]);
  const [modoEdicao, setModoEdicao] = useState(false);
  const [modoRemocao, setModoRemocao] = useState(false);
  const [motoristaSelecionado, setMotoristaSelecionado] = useState(null);
  const [formData, setFormData] = useState({});
  const [caminhoes, setCaminhoes] = useState([]);
  
  // Estados para modal de vale
  const [showModalVale, setShowModalVale] = useState(false);
  const [valeData, setValeData] = useState({
    motorista: null,
    valor: "",
    descricao: "",
    data: new Date().toISOString().split('T')[0]
  });
  
  const navigate = useNavigate();

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = () => {
    api
      .get("/api/motoristas/")
      .then((res) => setMotoristas(res.data))
      .catch((err) => console.error("Erro ao carregar motoristas:", err));

    api
      .get("/api/caminhoes/")
      .then((res) => setCaminhoes(res.data))
      .catch((err) => console.error("Erro ao carregar caminhões:", err));
  };

  const handleCardClick = (motorista) => {
    if (modoEdicao) {
      setMotoristaSelecionado(motorista);
      setFormData({ ...motorista });
    } else if (modoRemocao) {
      handleRemoverMotorista(motorista);
    } else {
      navigate(`/motoristas/${motorista.id}`);
    }
  };

  const handleEditarClick = () => {
    setModoEdicao(!modoEdicao);
    if (modoEdicao) {
      setMotoristaSelecionado(null);
    }
    if (modoRemocao) {
      setModoRemocao(false);
    }
  };

  const handleRemoverClick = () => {
    setModoRemocao(!modoRemocao);
    if (modoRemocao) {
      setMotoristaSelecionado(null);
    }
    if (modoEdicao) {
      setModoEdicao(false);
      setMotoristaSelecionado(null);
    }
  };

  const handleAdicionarValeClick = () => {
    if (motoristas.length === 0) {
      alert("Nenhum motorista cadastrado!");
      return;
    }
    setValeData({
      motorista: motoristas[0].id,
      valor: "",
      descricao: "",
      data: new Date().toISOString().split('T')[0]
    });
    setShowModalVale(true);
  };

  const handleRemoverMotorista = async (motorista) => {
    const confirmar = window.confirm(
      `Tem certeza que deseja remover o motorista "${motorista.nome}"?\nEsta ação não pode ser desfeita.`
    );

    if (!confirmar) return;

    try {
      await api.delete(`/api/motoristas/${motorista.id}/`);
      
      setMotoristas(motoristas.filter(m => m.id !== motorista.id));
      setModoRemocao(false);
      alert("Motorista removido com sucesso!");

    } catch (err) {
      console.error("Erro ao remover motorista:", err);
      alert("Erro ao remover motorista");
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleValeInputChange = (e) => {
    const { name, value } = e.target;
    setValeData({ ...valeData, [name]: value });
  };

  const getNomeCaminhao = (caminhaoId) => {
    if (!caminhaoId) return "—";
    const caminhao = caminhoes.find(c => c.id === caminhaoId);
    return caminhao ? caminhao.nome_conjunto : "—";
  };

  const isCaminhaoDisponivel = (caminhaoId) => {
    if (!caminhaoId) return true;
    
    return !motoristas.some(m => 
      m.caminhao === caminhaoId && m.id !== motoristaSelecionado?.id
    );
  };

  const handleSalvar = () => {
    if (formData.caminhao && !isCaminhaoDisponivel(parseInt(formData.caminhao))) {
      alert("Este caminhão já está sendo operado por outro motorista!");
      return;
    }

    api
      .put(`/api/motoristas/${motoristaSelecionado.id}/`, formData)
      .then((res) => {
        setMotoristas(
          motoristas.map((m) => (m.id === res.data.id ? res.data : m))
        );
        setMotoristaSelecionado(null);
        setModoEdicao(false);
        alert("Motorista atualizado com sucesso!");
      })
      .catch((err) => {
        console.error("Erro ao atualizar motorista:", err);
        alert("Erro ao atualizar motorista");
      });
  };

  const handleSalvarVale = async () => {
    if (!valeData.valor || parseFloat(valeData.valor) <= 0) {
      alert("Informe um valor válido!");
      return;
    }

    if (!valeData.motorista) {
      alert("Selecione um motorista!");
      return;
    }

    try {
      await api.post("/api/vales/", {
        motorista: valeData.motorista,
        valor: parseFloat(valeData.valor),
        descricao: valeData.descricao,
        data: valeData.data,
        pago: false
      });

      alert("Vale adicionado com sucesso!");
      setShowModalVale(false);
      setValeData({
        motorista: motoristas[0]?.id || null,
        valor: "",
        descricao: "",
        data: new Date().toISOString().split('T')[0]
      });
      carregarDados();

    } catch (err) {
      console.error("Erro ao adicionar vale:", err);
      alert("Erro ao adicionar vale");
    }
  };

  const handleCancelar = () => {
    setMotoristaSelecionado(null);
    setFormData({});
  };

  const handleCancelarVale = () => {
    setShowModalVale(false);
    setValeData({
      motorista: motoristas[0]?.id || null,
      valor: "",
      descricao: "",
      data: new Date().toISOString().split('T')[0]
    });
  };

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
          onClick={handleAdicionarValeClick}
        >
          ADICIONAR VALE
        </button>

        <button
          className={`white-btn ${modoEdicao ? 'active' : ''}`}
          onClick={handleEditarClick}
        >
          {modoEdicao ? 'CANCELAR EDIÇÃO' : 'EDITAR'}
        </button>

        <button
          className={`white-btn ${modoRemocao ? 'active-remover' : ''}`}
          onClick={handleRemoverClick}
        >
          {modoRemocao ? 'CANCELAR REMOÇÃO' : 'REMOVER'}
        </button>
      </div>

      {modoEdicao && !motoristaSelecionado && (
        <p className="modo-edicao-aviso">
          Clique em um card para editar o motorista
        </p>
      )}

      {modoRemocao && (
        <p className="modo-remocao-aviso">
          Clique em um card para remover o motorista
        </p>
      )}

      {/* Modal de Edição */}
      {motoristaSelecionado && (
        <div className="modal-overlay" onClick={handleCancelar}>
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>Editar Motorista</h2>
            
            <div className="form-group">
              <label>Nome:</label>
              <input
                type="text"
                name="nome"
                value={formData.nome || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label>CPF:</label>
              <input
                type="text"
                name="cpf"
                value={formData.cpf || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label>Idade:</label>
              <input
                type="number"
                name="idade"
                value={formData.idade || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label>Vencimento CNH:</label>
              <input
                type="date"
                name="venc_cnh"
                value={formData.venc_cnh || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group">
              <label>Vincular ao Conjunto:</label>
              <select
                name="caminhao"
                value={formData.caminhao || ''}
                onChange={handleInputChange}
              >
                <option value="">Nenhum</option>
                {caminhoes.map((c) => {
                  const disponivel = isCaminhaoDisponivel(c.id);
                  const jaVinculado = motoristaSelecionado?.caminhao === c.id;
                  
                  return (
                    <option 
                      key={c.id} 
                      value={c.id}
                      disabled={!disponivel && !jaVinculado}
                    >
                      {c.nome_conjunto} — {c.placa_cavalo}
                      {!disponivel && !jaVinculado ? ' (Em uso)' : ''}
                    </option>
                  );
                })}
              </select>
            </div>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={handleSalvar}>
                SALVAR
              </button>
              <button className="btn-cancelar" onClick={handleCancelar}>
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Adicionar Vale */}
      {showModalVale && (
        <div className="modal-overlay" onClick={handleCancelarVale}>
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>Adicionar Vale</h2>
            
            <div className="form-group">
              <label>Motorista:</label>
              <select
                name="motorista"
                value={valeData.motorista || ''}
                onChange={handleValeInputChange}
              >
                {motoristas.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Valor (R$):</label>
              <input
                type="number"
                name="valor"
                step="0.01"
                min="0"
                value={valeData.valor}
                onChange={handleValeInputChange}
                placeholder="0.00"
              />
            </div>

            <div className="form-group">
              <label>Descrição:</label>
              <textarea
                name="descricao"
                value={valeData.descricao}
                onChange={handleValeInputChange}
                placeholder="Descrição do vale (opcional)"
                rows="3"
              />
            </div>

            <div className="form-group">
              <label>Data:</label>
              <input
                type="date"
                name="data"
                value={valeData.data}
                onChange={handleValeInputChange}
              />
            </div>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={handleSalvarVale}>
                SALVAR
              </button>
              <button className="btn-cancelar" onClick={handleCancelarVale}>
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="cards-grid">
        {motoristas.map((m) => (
          <div
            key={m.id}
            className={`motorista-card ${modoEdicao ? 'editavel' : ''} ${modoRemocao ? 'removivel' : ''}`}
            onClick={() => handleCardClick(m)}
            style={{ cursor: 'pointer' }}
          >
            <h2 className="motorista-nome">{m.nome}</h2>

            <p><strong>CPF:</strong> {m.cpf}</p>
            <p><strong>Idade:</strong> {m.idade}</p>
            <p><strong>Venc. CNH:</strong> {m.venc_cnh}</p>

            <p>
              <strong>Caminhão:</strong>{" "}
              {getNomeCaminhao(m.caminhao)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Motoristas;