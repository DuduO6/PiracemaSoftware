import React, { useEffect, useState } from "react";
import api from "../api/api";
import "../styles/despesas.css";

const Despesas = () => {
  const [despesas, setDespesas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [caminhoes, setCaminhoes] = useState([]);

  const [mesAtual, setMesAtual] = useState(new Date().getMonth() + 1);
  const [anoAtual, setAnoAtual] = useState(new Date().getFullYear());

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
    mes: mesAtual,
    ano: anoAtual,
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
    const res = await api.get("/api/despesas/categorias/");
    setCategorias(res.data);
  };

  const carregarCaminhoes = async () => {
    const res = await api.get("/api/caminhoes/");
    setCaminhoes(res.data);
  };

  const carregarDespesas = async () => {
    const res = await api.get("/api/despesas/despesas/");
    setDespesas(res.data);
  };

  /* ==========================
     HELPERS
  =========================== */

  const voltarMes = () => {
    if (mesAtual === 1) {
      setMesAtual(12);
      setAnoAtual(a => a - 1);
    } else {
      setMesAtual(m => m - 1);
    }
  };

  const avancarMes = () => {
    if (mesAtual === 12) {
      setMesAtual(1);
      setAnoAtual(a => a + 1);
    } else {
      setMesAtual(m => m + 1);
    }
  };

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
     DESPESAS DO MÊS (CORRETO)
  =========================== */

  const despesasDoMes = despesas.filter(d => {
    const data = new Date(d.data_vencimento);
    return (
      data.getFullYear() === anoAtual &&
      data.getMonth() + 1 === mesAtual
    );
  });

  const balanco = despesasDoMes.reduce(
    (acc, d) => {
      const valor = Number(d.valor_total);

      acc.total += valor;
      if (d.status === "PAGO") acc.pago += valor;
      else acc.pendente += valor;

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
    } catch {
      alert("Erro ao pagar");
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

      <div className="navegacao">
        <button className="btn-nav" onClick={voltarMes}>◀</button>
        <span>{mesAtual}/{anoAtual}</span>
        <button className="btn-nav" onClick={avancarMes}>▶</button>
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

      <div className="btn-row">
        <button className="white-btn" onClick={() => setShowModalDespesa(true)}>
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
            {despesasDoMes.map(d => {
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
                    R$ {valorMes.toFixed(2)}
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
            })}
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
        <label className="form-label">Descrição</label>
        <input
          className="form-input"
          name="descricao"
          value={despesaData.descricao}
          onChange={handleDespesaInputChange}
        />
      </div>

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
        <label className="form-label">Tipo</label>
        <select
          className="form-input"
          name="tipo"
          value={despesaData.tipo}
          onChange={handleDespesaInputChange}
        >
          <option value="VARIAVEL">Variável</option>
          <option value="FIXA_ANUAL">Fixa anual</option>
          <option value="SALARIO">Salário</option>
        </select>
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

      {despesaData.tipo !== "SALARIO" && (
        <>
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
        </>
      )}

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
