import React, { useEffect, useState } from "react";
import api from "../api/api";
import "../styles/despesas.css";

const Despesas = () => {
  const [despesas, setDespesas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [caminhoes, setCaminhoes] = useState([]);
  const [motoristas, setMotoristas] = useState([]);

  const [showModalDespesa, setShowModalDespesa] = useState(false);

  const [despesaData, setDespesaData] = useState({
    categoria_id: "",
    caminhao_id: "",
    motorista_id: "",
    descricao: "",
    observacoes: "",
    valor: "",
    tipo: "OPERACIONAL",
    competencia: "",
    data_vencimento: "",
  });

  const [filtro, setFiltro] = useState({
    categoria: "",
    caminhao: "",
    motorista: "",
    status: "",
    tipo: "",
    ano: new Date().getFullYear(),
    mes: new Date().getMonth() + 1,
  });

  /* ==========================
     LOAD
  =========================== */

  useEffect(() => {
    carregarCategorias();
    carregarCaminhoes();
    carregarMotoristas();
    carregarDespesas();
  }, [filtro.ano, filtro.mes, filtro.caminhao, filtro.motorista, filtro.categoria, filtro.status, filtro.tipo]);

  
  const carregarCategorias = async () => {
    try {
      const res = await api.get("/api/despesas/categorias/");
      setCategorias(res.data);
    } catch (err) {
      console.error("Erro ao carregar categorias:", err);
    }
  };

  const carregarCaminhoes = async () => {
    try {
      const res = await api.get("/api/caminhoes/");
      setCaminhoes(res.data);
    } catch (err) {
      console.error("Erro ao carregar caminhões:", err);
    }
  };

  const carregarMotoristas = async () => {
    api.get("/api/motoristas/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || Object.values(res.data);
        setMotoristas(data);
      })
      .catch((err) => console.error("Erro ao carregar motoristas:", err));
  };

  const carregarDespesas = async () => {
    try {
      const params = {
        ano: filtro.ano,
        mes: filtro.mes,
      };

      if (filtro.caminhao) params.caminhao = filtro.caminhao;
      if (filtro.motorista) params.motorista = filtro.motorista; // ✅ ADICIONAR
      if (filtro.status) params.status = filtro.status;
      if (filtro.categoria) params.categoria = filtro.categoria;
      if (filtro.tipo) params.tipo = filtro.tipo;

      const res = await api.get("/api/despesas/despesas/", { params });
      setDespesas(res.data);
    } catch (err) {
      console.error("Erro ao carregar despesas:", err);
    }
  };


  /* ==========================
     HELPERS
  =========================== */

  const formatarData = d =>
    new Date(d + "T00:00:00").toLocaleDateString("pt-BR");

  const getNomeCategoria = c => c?.nome || "—";
  const getCorCategoria = c => c?.cor || "#9e9e9e";
  const getNomeCaminhao = c => c?.nome_conjunto || "—";
  const getNomeMotorista = m => m?.nome || "—";

  const getTipoClass = t => {
    if (t === "OPERACIONAL") return "tipo-fixa";
    return "tipo-variavel";
  };

  const getNomeTipo = t => {
    if (t === "OPERACIONAL") return "Operacional";
    return "Eventual";
  };

  const getStatusClass = s =>
    s === "PAGO" ? "status-pago" : "status-pendente";

  /* ==========================
     LÓGICA DE CATEGORIA
  =========================== */

  const categoriaEhSalario = () => {
    const cat = categorias.find(
      c => c.id === Number(despesaData.categoria_id)
    );

    if (!cat?.nome) return false;

    // Comparação direta, sem normalização desnecessária
    return cat.nome === "SALARIO" || cat.nome === "COMISSAO";
  };

  const categoriaRequerCaminhao = () => {
    return !categoriaEhSalario();
  };

  /* ==========================
     FILTROS
  =========================== */

  const handleFiltroChange = (campo, valor) => {
    setFiltro(prev => ({ ...prev, [campo]: valor }));
  };

  const limparFiltros = () => {
    setFiltro({
      categoria: "",
      caminhao: "",
      status: "",
      tipo: "",
      ano: new Date().getFullYear(),
      mes: new Date().getMonth() + 1,
    });
  };

  const removerFiltro = campo => {
    if (campo === "ano" || campo === "mes") return;
    setFiltro(prev => ({ ...prev, [campo]: "" }));
  };

  const getNomeFiltro = (campo, valor) => {
    if (campo === "categoria") {
      const cat = categorias.find(c => c.id === Number(valor));
      return cat ? cat.nome : "";
    }
    if (campo === "caminhao") {
      const cam = caminhoes.find(c => c.id === Number(valor));
      return cam ? cam.nome_conjunto : "";
    }
    if (campo === "status") {
      return valor === "PAGO" ? "Pago" : "Pendente";
    }
    if (campo === "tipo") {
      return valor === "OPERACIONAL" ? "Operacional" : "Eventual";
    }
    return valor;
  };

  const filtrosAtivos = Object.entries(filtro).filter(
    ([key, valor]) => valor !== "" && key !== "ano" && key !== "mes"
  );

  /* ==========================
     BALANÇO
  =========================== */

  const balanco = despesas.reduce(
    (acc, d) => {
      const valor = Number(d.valor);
      acc.total += valor;

      if (d.status === "PAGO") {
        acc.pago += valor;
      } else {
        acc.pendente += valor;
      }

      return acc;
    },
    { total: 0, pago: 0, pendente: 0 }
  );

  /* ==========================
     NAVEGAÇÃO DE PERÍODO
  =========================== */

  const navegarMes = direcao => {
    const novaData = new Date(filtro.ano, filtro.mes - 1);
    novaData.setMonth(novaData.getMonth() + direcao);

    setFiltro(prev => ({
      ...prev,
      ano: novaData.getFullYear(),
      mes: novaData.getMonth() + 1,
    }));
  };

  const getNomeMes = () => {
    const meses = [
      "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
      "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ];
    return `${meses[filtro.mes - 1]} ${filtro.ano}`;
  };

  /* ==========================
     FORM
  =========================== */

  const handleDespesaInputChange = e => {
    const { name, value } = e.target;
    
    setDespesaData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleCategoriaChange = e => {
    const categoria_id = e.target.value;
    setDespesaData(prev => ({
      ...prev,
      categoria_id,
      caminhao_id: "",
      motorista_id: "",
    }));
  };

  const abrirModalNovaDespesa = () => {
    // Define competência padrão como o mês atual do filtro
    const competencia = new Date(filtro.ano, filtro.mes - 1, 1)
      .toISOString()
      .split("T")[0];

    setDespesaData({
      categoria_id: "",
      caminhao_id: "",
      motorista_id: "",
      descricao: "",
      observacoes: "",
      valor: "",
      tipo: "OPERACIONAL",
      competencia: competencia,
      data_vencimento: "",
    });
    setShowModalDespesa(true);
  };

  const getCaminhaoOuMotorista = (despesa) => {
    if (despesa.motorista) {
      return getNomeMotorista(despesa.motorista);
    }

    if (despesa.caminhao) {
      return getNomeCaminhao(despesa.caminhao);
    }

    return "—";
  };


  const salvarDespesa = async () => {
    // Validações básicas
    if (!despesaData.categoria_id || !despesaData.descricao || !despesaData.valor) {
      alert("Preencha categoria, descrição e valor");
      return;
    }

    if (!despesaData.competencia) {
      alert("Preencha a competência (mês de referência)");
      return;
    }

    // Validação: SALÁRIO/COMISSÃO requer motorista
    if (categoriaEhSalario() && !despesaData.motorista_id) {
      alert("Selecione um motorista para salário/comissão");
      return;
    }

    // Validação: Outras categorias requerem caminhão
    if (categoriaRequerCaminhao() && !despesaData.caminhao_id) {
      alert("Selecione um caminhão para esta despesa");
      return;
    }

    try {
      const payload = {
        categoria_id: Number(despesaData.categoria_id),
        descricao: despesaData.descricao,
        observacoes: despesaData.observacoes || "",
        valor: Number(despesaData.valor),
        tipo: despesaData.tipo,
        competencia: despesaData.competencia,
      };

      // Adiciona caminhão apenas se não for salário/comissão
      if (categoriaRequerCaminhao() && despesaData.caminhao_id) {
        payload.caminhao_id = Number(despesaData.caminhao_id);
      }

      // Adiciona motorista se for salário/comissão
      if (categoriaEhSalario() && despesaData.motorista_id) {
        payload.motorista_id = Number(despesaData.motorista_id);
      }

      // Adiciona data de vencimento se preenchida
      if (despesaData.data_vencimento) {
        payload.data_vencimento = despesaData.data_vencimento;
      }

      console.log("📤 Payload enviado:", payload);

      await api.post("/api/despesas/despesas/", payload);

      alert("✅ Despesa criada com sucesso!");
      setShowModalDespesa(false);
      carregarDespesas();
    } catch (err) {
      console.error("❌ Erro completo:", err);
      console.error("📥 Resposta do servidor:", err.response?.data);
      
      // Tenta extrair mensagem de erro mais específica
      let errorMsg = "Erro desconhecido";
      if (err.response?.data) {
        if (typeof err.response.data === 'string') {
          errorMsg = err.response.data;
        } else if (err.response.data.detail) {
          errorMsg = err.response.data.detail;
        } else {
          errorMsg = JSON.stringify(err.response.data);
        }
      }
      
      alert("Erro ao salvar despesa: " + errorMsg);
    }
  };

  const marcarPago = async despesa => {
    try {
      await api.post(`/api/despesas/despesas/${despesa.id}/marcar_pago/`);
      carregarDespesas();
    } catch (err) {
      console.error("Erro ao marcar como pago:", err);
      alert("Erro ao marcar despesa como paga");
    }
  };

  const marcarPendente = async despesa => {
    try {
      await api.post(`/api/despesas/despesas/${despesa.id}/marcar_pendente/`);
      carregarDespesas();
    } catch (err) {
      console.error("Erro ao marcar como pendente:", err);
      alert("Erro ao marcar despesa como pendente");
    }
  };

  const excluirDespesa = async despesa => {
    if (!window.confirm(`Deseja realmente excluir a despesa "${despesa.descricao}"?`)) {
      return;
    }

    try {
      await api.delete(`/api/despesas/despesas/${despesa.id}/`);
      alert("✅ Despesa excluída com sucesso!");
      carregarDespesas();
    } catch (err) {
      console.error("Erro ao excluir despesa:", err);
      alert("Erro ao excluir despesa");
    }
  };

  /* ==========================
     RENDER
  =========================== */

  return (
    <div className="despesas-container">
      <h1 className="despesas-titulo">DESPESAS</h1>

      {/* NAVEGAÇÃO DE PERÍODO */}
      <div className="navegacao">
        <button className="btn-nav" onClick={() => navegarMes(-1)}>
          ◀
        </button>
        <span>{getNomeMes()}</span>
        <button className="btn-nav" onClick={() => navegarMes(1)}>
          ▶
        </button>
      </div>

      <div className="cards-row">
        <div className="card card-total">
          <span className="card-label">TOTAL</span>
          <span className="card-value">R$ {balanco.total.toFixed(2)}</span>
        </div>
        <div className="card card-pago">
          <span className="card-label">PAGO</span>
          <span className="card-value">R$ {balanco.pago.toFixed(2)}</span>
        </div>
        <div className="card card-pendente">
          <span className="card-label">PENDENTE</span>
          <span className="card-value">R$ {balanco.pendente.toFixed(2)}</span>
        </div>
      </div>

      {/* FILTROS */}
      <div className="filtros-section">
        <div className="filtros-grid">
          <div className="filtro-item">
            <label className="filtro-label">Categoria</label>
            <select
              className="filtro-select"
              value={filtro.categoria}
              onChange={e => handleFiltroChange("categoria", e.target.value)}
            >
              <option value="">Todas</option>
              {categorias.map(c => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="filtro-item">
            <label className="filtro-label">Caminhão</label>
            <select
              className="filtro-select"
              value={filtro.caminhao}
              onChange={e => handleFiltroChange("caminhao", e.target.value)}
            >
              <option value="">Todos</option>
              {caminhoes.map(c => (
                <option key={c.id} value={c.id}>
                  {c.nome_conjunto}
                </option>
              ))}
            </select>
          </div>

          <div className="filtro-item">
            <label className="filtro-label">Motorista</label>
            <select
              className="filtro-select"
              value={filtro.motorista}
              onChange={e => handleFiltroChange("motorista", e.target.value)}
            >
              <option value="">Todos</option>
              {motoristas.map(m => (
                <option key={m.id} value={m.id}>
                  {m.nome}
                </option>
              ))}
            </select>
          </div>


          <div className="filtro-item">
            <label className="filtro-label">Status</label>
            <select
              className="filtro-select"
              value={filtro.status}
              onChange={e => handleFiltroChange("status", e.target.value)}
            >
              <option value="">Todos</option>
              <option value="PAGO">Pago</option>
              <option value="PENDENTE">Pendente</option>
            </select>
          </div>

          <div className="filtro-item">
            <label className="filtro-label">Tipo</label>
            <select
              className="filtro-select"
              value={filtro.tipo}
              onChange={e => handleFiltroChange("tipo", e.target.value)}
            >
              <option value="">Todos</option>
              <option value="OPERACIONAL">Operacional</option>
              <option value="EVENTUAL">Eventual</option>
            </select>
          </div>
        </div>

        {filtrosAtivos.length > 0 && (
          <div className="filtros-aplicados">
            <span className="filtros-label">Filtros ativos:</span>
            {filtrosAtivos.map(([campo, valor]) => (
              <div key={campo} className="filtro-badge">
                <span>{getNomeFiltro(campo, valor)}</span>
                <button
                  className="filtro-remover"
                  onClick={() => removerFiltro(campo)}
                >
                  ✕
                </button>
              </div>
            ))}
            <button className="filtro-limpar" onClick={limparFiltros}>
              Limpar todos
            </button>
          </div>
        )}
      </div>

      <div className="btn-row">
        <button className="white-btn" onClick={abrirModalNovaDespesa}>
          NOVA DESPESA
        </button>
      </div>

      <div className="table-wrapper">
        <table className="table-custom">
          <thead>
            <tr>
              <th>COMPETÊNCIA</th>
              <th>CATEGORIA</th>
              <th>CAMINHÃO/MOTORISTA</th>
              <th>DESCRIÇÃO</th>
              <th>VALOR</th>
              <th>TIPO</th>
              <th>VENCIMENTO</th>
              <th>STATUS</th>
              <th>AÇÕES</th>
            </tr>
          </thead>

          <tbody>
            {despesas.length === 0 ? (
              <tr>
                <td colSpan="9" style={{ textAlign: "center", padding: "40px" }}>
                  <div style={{ fontSize: "18px", color: "#999" }}>
                    {filtrosAtivos.length > 0
                      ? "Nenhuma despesa encontrada com os filtros aplicados"
                      : "Nenhuma despesa registrada neste mês"}
                  </div>
                </td>
              </tr>
            ) : (
              despesas.map(d => (
                <tr key={d.id}>
                  <td>{d.competencia_formatada}</td>
                  <td>
                    <span
                      className="categoria-badge"
                      style={{ background: getCorCategoria(d.categoria) }}
                    >
                      {getNomeCategoria(d.categoria)}
                    </span>
                  </td>
                  <td>{getCaminhaoOuMotorista(d)}</td>
                  <td>{d.descricao}</td>
                  <td>R$ {parseFloat(d.valor || 0).toFixed(2)}</td>
                  <td>
                    <span className={`status-badge ${getTipoClass(d.tipo)}`}>
                      {getNomeTipo(d.tipo)}
                    </span>
                  </td>
                  <td>
                    {d.data_vencimento ? formatarData(d.data_vencimento) : "—"}
                  </td>
                  <td>
                    <span className={`status-badge ${getStatusClass(d.status)}`}>
                      {d.status}
                    </span>
                  </td>
                  <td>
                    <div className="acoes-row">
                      {d.status === "PENDENTE" ? (
                        <button className="btn-pagar" onClick={() => marcarPago(d)}>
                          PAGAR
                        </button>
                      ) : (
                        <button className="btn-editar" onClick={() => marcarPendente(d)}>
                          DESFAZER
                        </button>
                      )}
                      <button className="btn-remover" onClick={() => excluirDespesa(d)}>
                        APAGAR
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModalDespesa && (
        <div className="modal-overlay" onClick={() => setShowModalDespesa(false)}>
          <div className="modal-custom" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">Nova Despesa</h2>

            <div className="form-group">
              <label className="form-label">Categoria *</label>
              <select
                className="form-input"
                name="categoria_id"
                value={despesaData.categoria_id}
                onChange={handleCategoriaChange}
              >
                <option value="">Selecione</option>
                {categorias.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
              </select>
            </div>

            {/* CAMPO CONDICIONAL: MOTORISTA (apenas para SALÁRIO/COMISSÃO) */}
            {categoriaEhSalario() && (
              <div className="form-group">
                <label className="form-label">Motorista *</label>
                <select
                  className="form-input"
                  name="motorista_id"
                  value={despesaData.motorista_id}
                  onChange={handleDespesaInputChange}
                >
                  <option value="">Selecione o motorista</option>
                  {motoristas.map(m => (
                    <option key={m.id} value={m.id}>
                      {m.nome}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* CAMPO CONDICIONAL: CAMINHÃO (não aparece para SALÁRIO/COMISSÃO) */}
            {categoriaRequerCaminhao() && (
              <div className="form-group">
                <label className="form-label">Caminhão *</label>
                <select
                  className="form-input"
                  name="caminhao_id"
                  value={despesaData.caminhao_id}
                  onChange={handleDespesaInputChange}
                >
                  <option value="">Selecione</option>
                  {caminhoes.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.nome_conjunto}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Descrição *</label>
              <input
                className="form-input"
                name="descricao"
                value={despesaData.descricao}
                onChange={handleDespesaInputChange}
                placeholder={categoriaEhSalario() ? "Ex: Salário João Silva - Janeiro/2025" : "Ex: IPVA Janeiro 2025"}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Tipo *</label>
              <select
                className="form-input"
                name="tipo"
                value={despesaData.tipo}
                onChange={handleDespesaInputChange}
              >
                <option value="OPERACIONAL">Operacional</option>
                <option value="EVENTUAL">Eventual</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Valor *</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                name="valor"
                value={despesaData.valor}
                onChange={handleDespesaInputChange}
                placeholder="0.00"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Competência (Mês de referência) *</label>
              <input
                type="date"
                className="form-input"
                name="competencia"
                value={despesaData.competencia}
                onChange={handleDespesaInputChange}
              />
              <small style={{ color: "#999", fontSize: "12px", marginTop: "4px", display: "block" }}>
                Mês ao qual esta despesa pertence
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">Data de vencimento (opcional)</label>
              <input
                type="date"
                className="form-input"
                name="data_vencimento"
                value={despesaData.data_vencimento}
                onChange={handleDespesaInputChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Observações</label>
              <textarea
                className="form-input"
                name="observacoes"
                rows="3"
                value={despesaData.observacoes}
                onChange={handleDespesaInputChange}
              />
            </div>

            <div className="modal-buttons">
              <button className="btn-salvar" onClick={salvarDespesa}>
                SALVAR
              </button>
              <button
                className="btn-cancelar"
                onClick={() => setShowModalDespesa(false)}
              >
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Despesas;