import React, { useEffect, useState } from "react";
import api from "../api/api";
import "../styles/despesas.css";

const Despesas = () => {
  const [despesas, setDespesas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [caminhoes, setCaminhoes] = useState([]);


  const [showModalDespesa, setShowModalDespesa] = useState(false);
  const [modoEdicao, setModoEdicao] = useState(false);

  const [despesaData, setDespesaData] = useState({
    id: null,
    categoria_id: "",
    caminhao_id: "",
    descricao: "",
    observacoes: "",
    valor_total: "",
    tipo: "VARIAVEL",
    data_vencimento: "",
    status: "PENDENTE",
  });

  const [filtro, setFiltro] = useState({
    categoria: "",
    caminhao: "",
    status: "",
    tipo: "",
    inicio: "",
    fim: "",
  });

  /* ==========================
     LOAD
  =========================== */

  useEffect(() => {
    carregarCategorias();
    carregarCaminhoes();
    carregarDespesas();
  }, []);

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

  const carregarDespesas = async () => {
    try {
      const res = await api.get("/api/despesas/despesas/");
      setDespesas(res.data);
    } catch (err) {
      console.error("Erro ao carregar despesas:", err);
    }
  };

  /* ==========================
     HELPERS
  =========================== */

  const formatarData = d =>
    new Date(d).toLocaleDateString("pt-BR");

  const getNomeCategoria = c => c?.nome || "—";
  const getCorCategoria = c => c?.cor || "#9e9e9e";
  const getNomeCaminhao = c => c?.nome_conjunto || "—";

  const getTipoClass = t => {
    if (t === "FIXA_ANUAL") return "tipo-fixa";
    if (t === "FIXA_MENSAL") return "tipo-recorrente";
    return "tipo-variavel";
  };

  const getNomeTipo = t => {
    if (t === "FIXA_ANUAL") return "Fixa anual";
    if (t === "FIXA_MENSAL") return "Salário";
    return "Variável";
  };

  const getStatusClass = s =>
    s === "PAGO" ? "status-pago" : "status-pendente";

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
      inicio: "",
      fim: "",
    });
  };

  const removerFiltro = campo => {
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
      if (valor === "FIXA_ANUAL") return "Fixa Anual";
      if (valor === "FIXA_MENSAL") return "Salário";
      return "Variável";
    }
    return valor;
  };

  const filtrosAtivos = Object.entries(filtro).filter(([_, valor]) => valor !== "");

  /* ==========================
     DESPESAS FILTRADAS
  =========================== */

  const despesasFiltradas = despesas.filter(d => {
  const data = new Date(d.data_vencimento);

  // Intervalo de datas
  if (filtro.inicio && data < new Date(filtro.inicio)) return false;
  if (filtro.fim && data > new Date(filtro.fim)) return false;

  // Categoria
  if (
    filtro.categoria &&
    d.categoria?.id !== Number(filtro.categoria)
  ) return false;

  // Caminhão
  if (
    filtro.caminhao &&
    d.caminhao?.id !== Number(filtro.caminhao)
  ) return false;

  // Status
  if (filtro.status && d.status !== filtro.status) return false;

  // Tipo
  if (filtro.tipo && d.tipo !== filtro.tipo) return false;

  return true;
});

  const balanco = despesasFiltradas.reduce(
    (acc, d) => {
      const valorMes =
        d.tipo === "FIXA_ANUAL"
          ? Number(d.valor_total) / 12
          : Number(d.valor_total);

      acc.total += valorMes;

      if (d.status === "PAGO") {
        acc.pago += valorMes;
      } else {
        acc.pendente += valorMes;
      }

      return acc;
    },
    { total: 0, pago: 0, pendente: 0 }
  );



  /* ==========================
     FORM
  =========================== */

  const handleDespesaInputChange = e => {
    const { name, value } = e.target;
    setDespesaData(prev => ({ ...prev, [name]: value }));
  };

  const abrirModalNovaDespesa = () => {
    setModoEdicao(false);
    setDespesaData({
      id: null,
      categoria_id: "",
      caminhao_id: "",
      descricao: "",
      observacoes: "",
      valor_total: "",
      tipo: "VARIAVEL",
      data_vencimento: "",
      status: "PENDENTE",
    });
    setShowModalDespesa(true);
  };

  const salvarDespesa = async () => {
    if (
      !despesaData.descricao ||
      !despesaData.categoria_id ||
      !despesaData.valor_total ||
      !despesaData.data_vencimento
    ) {
      alert("Preencha os campos obrigatórios");
      return;
    }

    try {
      if (modoEdicao) {
        // Editar despesa existente
        await api.put(`/api/despesas/despesas/${despesaData.id}/`, {
          categoria_id: Number(despesaData.categoria_id),
          caminhao_id: despesaData.caminhao_id ? Number(despesaData.caminhao_id) : null,
          descricao: despesaData.descricao,
          observacoes: despesaData.observacoes || "",
          valor_total: despesaData.valor_total,
          tipo: despesaData.tipo,
          data_vencimento: despesaData.data_vencimento,
          status: despesaData.status,
        });
      } else {
        // Criar nova despesa
        if (despesaData.tipo === "FIXA_ANUAL") {
          await api.post(
            "/api/despesas/despesas/criar_despesa_fixa_anual/",
            {
              categoria_id: Number(despesaData.categoria_id),
              caminhao_id: despesaData.caminhao_id
                ? Number(despesaData.caminhao_id)
                : null,
              descricao: despesaData.descricao,
              valor_total: despesaData.valor_total,
              data_inicio: despesaData.data_vencimento,
              observacoes: despesaData.observacoes || "",
            }
          );
        } else {
          await api.post("/api/despesas/despesas/", {
            categoria_id: Number(despesaData.categoria_id),
            caminhao_id: despesaData.caminhao_id
              ? Number(despesaData.caminhao_id)
              : null,
            descricao: despesaData.descricao,
            observacoes: despesaData.observacoes || "",
            valor_total: despesaData.valor_total,
            tipo: despesaData.tipo,
            data_vencimento: despesaData.data_vencimento,
            status: despesaData.status,
          });
        }
      }

      setShowModalDespesa(false);
      setModoEdicao(false);
      carregarDespesas();
    } catch (err) {
      console.error(err.response?.data);
      alert("Erro ao salvar despesa");
    }
  };

  const pagarDespesa = async d => {
    try {
      await api.put(`/api/despesas/despesas/${d.id}/`, {
        categoria_id: d.categoria.id,
        caminhao_id: d.caminhao?.id || null,
        descricao: d.descricao,
        observacoes: d.observacoes || "",
        valor_total: d.valor_total,
        tipo: d.tipo,
        data_vencimento: d.data_vencimento,
        status: "PAGO",
      });

      carregarDespesas();
    } catch (err) {
      console.error("Erro ao pagar:", err);
      alert("Erro ao pagar despesa");
    }
  };

  const editarDespesa = d => {
    setModoEdicao(true);
    setShowModalDespesa(true);

    setDespesaData({
      id: d.id,
      categoria_id: d.categoria?.id || "",
      caminhao_id: d.caminhao?.id || "",
      descricao: d.descricao || "",
      observacoes: d.observacoes || "",
      valor_total: d.valor_total,
      tipo: d.tipo,
      data_vencimento: d.data_vencimento,
      status: d.status,
    });
  };

  const removerDespesa = async d => {
    const confirmar = window.confirm(
      "Tem certeza que deseja remover esta despesa?"
    );

    if (!confirmar) return;

    try {
      await api.delete(`/api/despesas/despesas/${d.id}/`);
      carregarDespesas();
    } catch (err) {
      console.error("Erro ao remover:", err.response?.data);
      alert("Erro ao remover despesa");
    }
  };

  /* ==========================
     RENDER
  =========================== */

  return (
    <div className="despesas-container">
      <h1 className="despesas-titulo">DESPESAS</h1>

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
              <option value="VARIAVEL">Variável</option>
              <option value="FIXA_ANUAL">Fixa Anual</option>
              <option value="FIXA_MENSAL">Salário</option>
            </select>
          </div>

          <div className="filtro-item">
  <label className="filtro-label">Início</label>
  <input
    type="date"
    className="filtro-select"
    value={filtro.inicio}
    onChange={e => handleFiltroChange("inicio", e.target.value)}
  />
</div>

<div className="filtro-item">
  <label className="filtro-label">Fim</label>
  <input
    type="date"
    className="filtro-select"
    value={filtro.fim}
    onChange={e => handleFiltroChange("fim", e.target.value)}
  />
</div>

        </div>

        {/* FILTROS ATIVOS */}
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
              <th>DATA</th>
              <th>CATEGORIA</th>
              <th>CAMINHÃO</th>
              <th>DESCRIÇÃO</th>
              <th>VALOR (MÊS)</th>
              <th>TIPO</th>
              <th>STATUS</th>
              <th>AÇÕES</th>
            </tr>
          </thead>

          <tbody>
            {despesasFiltradas.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: "center", padding: "40px" }}>
                  <div style={{ fontSize: "18px", color: "#999" }}>
                    {filtrosAtivos.length > 0
                      ? "Nenhuma despesa encontrada com os filtros aplicados"
                      : "Nenhuma despesa registrada neste mês"}
                  </div>
                </td>
              </tr>
            ) : (
              despesasFiltradas.map(d => {
                const valorMes =
                  d.tipo === "FIXA_ANUAL"
                    ? d.valor_total / 12
                    : d.valor_total;

                return (
                  <tr key={d.id}>
                    <td>{formatarData(d.data_vencimento)}</td>
                    <td>
                      <span
                        className="categoria-badge"
                        style={{ background: getCorCategoria(d.categoria) }}
                      >
                        {getNomeCategoria(d.categoria)}
                      </span>
                    </td>
                    <td>{getNomeCaminhao(d.caminhao)}</td>
                    <td>{d.descricao}</td>
                    <td>
                      R$ {parseFloat(valorMes || 0).toFixed(2)}
                      {d.tipo === "FIXA_ANUAL" && (
                        <div className="parcela-info">
                          Total anual: R$ {Number(d.valor_total).toFixed(2)}
                        </div>
                      )}
                    </td>
                    <td>
                      <span className={`status-badge ${getTipoClass(d.tipo)}`}>
                        {getNomeTipo(d.tipo)}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge ${getStatusClass(d.status)}`}>
                        {d.status}
                      </span>
                    </td>
                    <td>
                      <div className="acoes-row">
                        <button className="btn-editar" onClick={() => editarDespesa(d)}>EDITAR</button>
                        {d.status !== "PAGO" && (
                          <button className="btn-pagar" onClick={() => pagarDespesa(d)}>PAGAR</button>
                        )}
                        <button className="btn-remover" onClick={() => removerDespesa(d)}>REMOVER</button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {showModalDespesa && (
        <div className="modal-overlay" onClick={() => setShowModalDespesa(false)}>
          <div className="modal-custom" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">
              {modoEdicao ? "Editar Despesa" : "Nova Despesa"}
            </h2>

            <div className="form-group">
              <label className="form-label">Categoria</label>
              <select
                className="form-input"
                name="categoria_id"
                value={despesaData.categoria_id}
                onChange={handleDespesaInputChange}
              >
                <option value="">Selecione</option>
                {categorias.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Caminhão</label>
              <select
                className="form-input"
                name="caminhao_id"
                value={despesaData.caminhao_id}
                onChange={handleDespesaInputChange}
              >
                <option value="">—</option>
                {caminhoes.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.nome_conjunto}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Tipo</label>
              <select
                className="form-input"
                name="tipo"
                value={despesaData.tipo}
                onChange={handleDespesaInputChange}
              >
                <option value="VARIAVEL">Variável</option>
                <option value="FIXA_ANUAL">Fixa anual</option>
                <option value="FIXA_MENSAL">Salário</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Descrição</label>
              <input
                className="form-input"
                name="descricao"
                value={despesaData.descricao}
                onChange={handleDespesaInputChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Valor total</label>
              <input
                type="number"
                className="form-input"
                name="valor_total"
                value={despesaData.valor_total}
                onChange={handleDespesaInputChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Data de vencimento</label>
              <input
                type="date"
                className="form-input"
                name="data_vencimento"
                value={despesaData.data_vencimento}
                onChange={handleDespesaInputChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Status</label>
              <select
                className="form-input"
                name="status"
                value={despesaData.status}
                onChange={handleDespesaInputChange}
              >
                <option value="PENDENTE">Pendente</option>
                <option value="PAGO">Pago</option>
              </select>
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