import React, { useEffect, useState } from "react";
import api from "../api/api";
import "../styles/viagens.css";

const Viagens = () => {
  const [viagens, setViagens] = useState([]);
  const [motoristas, setMotoristas] = useState([]);
  const [valorTotalGeral, setValorTotalGeral] = useState(0);

  // Modal de adicionar/editar viagem
  const [showModalViagem, setShowModalViagem] = useState(false);
  const [modoEdicao, setModoEdicao] = useState(false);
  const [viagemData, setViagemData] = useState({
    id: null,
    motorista: "",
    origem: "",
    destino: "",
    cliente: "",
    peso: "",
    valor_tonelada: "",
    data: "",
    pago: false,
  });

  const [showFiltro, setShowFiltro] = useState(false);
  const [filtro, setFiltro] = useState({
    motorista: "",
    cliente: "",
    localidade: "",
    pago: "",
    inicio: "",
    fim: ""
  });

  const [showAcertoModal, setShowAcertoModal] = useState(false);
  const [acertoData, setAcertoData] = useState({
    motorista: "",
    inicio: "",
    fim: ""
  });

  // Carregar motoristas
  useEffect(() => {
    api.get("/api/motoristas/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || Object.values(res.data);
        setMotoristas(data);

        if (data.length > 0 && !viagemData.motorista) {
          setViagemData((prev) => ({ ...prev, motorista: data[0].id }));
        }
      })
      .catch((err) => console.error("Erro ao carregar motoristas:", err));
  }, []);

  // Carregar viagens
  useEffect(() => {
    api.get("/api/viagens/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || Object.values(res.data);
        setViagens(data);
        const somaGeral = data.reduce((acc, v) => acc + Number(v.valor_total || 0), 0);
        setValorTotalGeral(somaGeral);
      })
      .catch((err) => console.error("Erro ao carregar viagens:", err));
  }, []);

  // Geração de acerto (PDF)
  const gerarAcerto = (motoristaId, inicio, fim) => {
    api.get("/api/viagens/gerar_acerto/", {
      params: { motorista_id: motoristaId, inicio, fim },
      responseType: "blob",
    })
      .then((res) => {
        const blob = new Blob([res.data], { type: "application/pdf" });
        const link = document.createElement("a");
        link.href = window.URL.createObjectURL(blob);
        link.download = `Acerto_${motoristaId}.pdf`;
        link.click();
      })
      .catch((err) => console.error("Erro ao gerar PDF:", err));
  };

  // Handlers do modal
  const handleViagemInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setViagemData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleAdicionarViagem = () => {
    if (!viagemData.motorista || !viagemData.origem || !viagemData.destino || !viagemData.cliente || !viagemData.peso || !viagemData.valor_tonelada || !viagemData.data) {
      alert("Preencha todos os campos obrigatórios!");
      return;
    }

    const payload = {
      ...viagemData,
      motorista: Number(viagemData.motorista),
    };

    if (modoEdicao && viagemData.id) {
      // Editar viagem existente
      api.put(`/api/viagens/${viagemData.id}/`, payload)
        .then((res) => {
          setViagens((prev) => prev.map(v => v.id === viagemData.id ? res.data : v));
          fecharModal();
        })
        .catch((err) => console.error("Erro ao editar viagem:", err));
    } else {
      // Adicionar nova viagem
      api.post("/api/viagens/", payload)
        .then((res) => {
          setViagens((prev) => [...prev, res.data]);
          fecharModal();
        })
        .catch((err) => console.error("Erro ao adicionar viagem:", err));
    }
  };

  const handleEditarViagem = (viagem) => {
    setModoEdicao(true);
    setViagemData({
      id: viagem.id,
      motorista: viagem.motorista,
      origem: viagem.origem,
      destino: viagem.destino,
      cliente: viagem.cliente,
      peso: viagem.peso,
      valor_tonelada: viagem.valor_tonelada,
      data: viagem.data,
      pago: viagem.pago,
    });
    setShowModalViagem(true);
  };

  const abrirModalNovo = () => {
    setModoEdicao(false);
    setViagemData({
      id: null,
      motorista: motoristas[0]?.id || "",
      origem: "",
      destino: "",
      cliente: "",
      peso: "",
      valor_tonelada: "",
      data: "",
      pago: false,
    });
    setShowModalViagem(true);
  };

  const fecharModal = () => {
    setShowModalViagem(false);
    setModoEdicao(false);
    setViagemData({
      id: null,
      motorista: motoristas[0]?.id || "",
      origem: "",
      destino: "",
      cliente: "",
      peso: "",
      valor_tonelada: "",
      data: "",
      pago: false,
    });
  };

  // Aplicar filtros - agora filtra de verdade
  const aplicarFiltro = () => {
    setShowFiltro(false);
  };

  const limparFiltros = () => {
    setFiltro({
      motorista: "",
      cliente: "",
      localidade: "",
      pago: "",
      inicio: "",
      fim: ""
    });
  };

  // Filtrar viagens em tempo real
  const viagensFiltradas = viagens.filter(v => {
    if (filtro.motorista && v.motorista != filtro.motorista) return false;
    if (filtro.cliente && !v.cliente.toLowerCase().includes(filtro.cliente.toLowerCase())) return false;
    if (filtro.localidade && 
        !v.origem.toLowerCase().includes(filtro.localidade.toLowerCase()) &&
        !v.destino.toLowerCase().includes(filtro.localidade.toLowerCase())) return false;
    if (filtro.pago === "nao_pago" && v.pago === true) return false;
    if (filtro.inicio && new Date(v.data) < new Date(filtro.inicio)) return false;
    if (filtro.fim && new Date(v.data) > new Date(filtro.fim)) return false;
    return true;
  });

  const valorTotalFiltrado = viagensFiltradas.reduce((acc, v) => acc + Number(v.valor_total || 0), 0);
  const temFiltroAtivo = filtro.motorista || filtro.cliente || filtro.localidade || filtro.pago || filtro.inicio || filtro.fim;

  return (
    <div className="viagens-container">
      <h1 className="titulo">VIAGENS</h1>

      <div className="btn-row">
        <button className="white-btn" onClick={abrirModalNovo}>
          NOVA VIAGEM
        </button>
        <button className="white-btn" onClick={() => setShowFiltro(true)}>
          FILTRAR
        </button>
        <button className="white-btn" onClick={() => setShowAcertoModal(true)}>
          GERAR ACERTO
        </button>
      </div>

      <div className="info-viagens">
        <p className="total-text">
          TOTAL DE VIAGENS: {viagensFiltradas.length}
        </p>
        <p className="total-valor">
          VALOR TOTAL: R$ {valorTotalFiltrado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
        </p>
      </div>

      {temFiltroAtivo && (
        <div className="filtros-aplicados">
          {filtro.motorista && <span className="filtro-badge">Motorista: {motoristas.find(m => m.id == filtro.motorista)?.nome}</span>}
          {filtro.cliente && <span className="filtro-badge">Cliente: {filtro.cliente}</span>}
          {filtro.localidade && <span className="filtro-badge">Localidade: {filtro.localidade}</span>}
          {filtro.pago && <span className="filtro-badge">Não pagos</span>}
          {filtro.inicio && <span className="filtro-badge">Desde: {filtro.inicio}</span>}
          {filtro.fim && <span className="filtro-badge">Até: {filtro.fim}</span>}
          <button className="filtro-badge filtro-limpar" onClick={limparFiltros}>✕ Limpar</button>
        </div>
      )}

      <div className="table-wrapper">
        <table className="viagens-table">
          <thead>
            <tr>
              <th>DATA</th>
              <th>ORIGEM</th>
              <th>DESTINO</th>
              <th>CLIENTE</th>
              <th>PESO(TN)</th>
              <th>VALOR P/TN</th>
              <th>VALOR</th>
              <th>PAGO</th>
              <th>MOTORISTA</th>
              <th>AÇÕES</th>
            </tr>
          </thead>
          <tbody>
            {viagensFiltradas.map(v => (
              <tr key={v.id}>
                <td>{v.data}</td>
                <td>{v.origem}</td>
                <td>{v.destino}</td>
                <td>{v.cliente}</td>
                <td>{v.peso}</td>
                <td>R$ {Number(v.valor_tonelada).toFixed(2)}</td>
                <td>R$ {Number(v.valor_total).toFixed(2)}</td>
                <td>
                  <span className={`status-badge ${v.pago ? 'status-pago' : 'status-pendente'}`}>
                    {v.pago ? "PAGO" : "PENDENTE"}
                  </span>
                </td>
                <td>{motoristas.find(m => m.id === v.motorista)?.nome || "—"}</td>
                <td>
                  <button className="btn-editar" onClick={() => handleEditarViagem(v)}>
                    EDITAR
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal Filtro */}
      {showFiltro && (
        <div className="modal-overlay" onClick={() => setShowFiltro(false)}>
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>Filtrar Viagens</h2>

            <div className="form-group">
              <label>Motorista:</label>
              <select
                value={filtro.motorista}
                onChange={e => setFiltro({ ...filtro, motorista: e.target.value })}
              >
                <option value="">Todos</option>
                {motoristas.map(m => (
                  <option key={m.id} value={m.id}>{m.nome}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Cliente:</label>
              <input
                type="text"
                value={filtro.cliente}
                onChange={e => setFiltro({ ...filtro, cliente: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Localidade (Origem ou Destino):</label>
              <input
                type="text"
                value={filtro.localidade}
                onChange={e => setFiltro({ ...filtro, localidade: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Pagamento:</label>
              <select
                value={filtro.pago}
                onChange={e => setFiltro({ ...filtro, pago: e.target.value })}
              >
                <option value="">Todos</option>
                <option value="nao_pago">Apenas Não Pagos</option>
              </select>
            </div>

            <div className="form-group">
              <label>Período:</label>
              <div className="date-range">
                <input
                  type="date"
                  value={filtro.inicio}
                  onChange={e => setFiltro({ ...filtro, inicio: e.target.value })}
                />
                <span>até</span>
                <input
                  type="date"
                  value={filtro.fim}
                  onChange={e => setFiltro({ ...filtro, fim: e.target.value })}
                />
              </div>
            </div>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={aplicarFiltro}>APLICAR</button>
              <button className="btn-cancelar" onClick={() => setShowFiltro(false)}>CANCELAR</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Viagem */}
      {showModalViagem && (
        <div className="modal-overlay" onClick={fecharModal}>
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>{modoEdicao ? "Editar Viagem" : "Nova Viagem"}</h2>

            <div className="form-group">
              <label>Motorista:</label>
              <select
                name="motorista"
                value={viagemData.motorista}
                onChange={handleViagemInputChange}
              >
                {motoristas.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Origem:</label>
              <input
                type="text"
                name="origem"
                value={viagemData.origem}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group">
              <label>Destino:</label>
              <input
                type="text"
                name="destino"
                value={viagemData.destino}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group">
              <label>Cliente:</label>
              <input
                type="text"
                name="cliente"
                value={viagemData.cliente}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group">
              <label>Peso (TN):</label>
              <input
                type="number"
                name="peso"
                value={viagemData.peso}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group">
              <label>Valor / TN:</label>
              <input
                type="number"
                name="valor_tonelada"
                value={viagemData.valor_tonelada}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group">
              <label>Data:</label>
              <input
                type="date"
                name="data"
                value={viagemData.data}
                onChange={handleViagemInputChange}
              />
            </div>

            <div className="form-group-checkbox">
              <input
                type="checkbox"
                name="pago"
                id="pago"
                checked={viagemData.pago}
                onChange={handleViagemInputChange}
              />
              <label htmlFor="pago">Marcar como pago</label>
            </div>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={handleAdicionarViagem}>
                {modoEdicao ? "SALVAR" : "ADICIONAR"}
              </button>
              <button className="btn-cancelar" onClick={fecharModal}>
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Acerto */}
      {showAcertoModal && (
        <div className="modal-overlay" onClick={() => setShowAcertoModal(false)}>
          <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
            <h2>Gerar Acerto</h2>

            <div className="form-group">
              <label>Motorista:</label>
              <select
                value={acertoData.motorista}
                onChange={e => setAcertoData({ ...acertoData, motorista: e.target.value })}
              >
                <option value="">Selecione</option>
                {motoristas.map(m => (
                  <option key={m.id} value={m.id}>{m.nome}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Período:</label>
              <div className="date-range">
                <input
                  type="date"
                  value={acertoData.inicio}
                  onChange={e => setAcertoData({ ...acertoData, inicio: e.target.value })}
                />
                <span>até</span>
                <input
                  type="date"
                  value={acertoData.fim}
                  onChange={e => setAcertoData({ ...acertoData, fim: e.target.value })}
                />
              </div>
            </div>

            <div className="modal-buttons">
              <button
                className="btn-salvar"
                onClick={() => {
                  if (!acertoData.motorista || !acertoData.inicio || !acertoData.fim) {
                    alert("Selecione motorista e período!");
                    return;
                  }
                  gerarAcerto(acertoData.motorista, acertoData.inicio, acertoData.fim);
                  setShowAcertoModal(false);
                }}
              >
                GERAR PDF
              </button>
              <button className="btn-cancelar" onClick={() => setShowAcertoModal(false)}>
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Viagens;