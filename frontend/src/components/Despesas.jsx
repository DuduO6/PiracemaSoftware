import React, { useEffect, useState } from "react";
import api from "../api/api";
import "../styles/despesas.css";

const Despesas = () => {
  const [despesas, setDespesas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [caminhoes, setCaminhoes] = useState([]);
  const [valorTotalGeral, setValorTotalGeral] = useState(0);
  const [valorPago, setValorPago] = useState(0);
  const [valorPendente, setValorPendente] = useState(0);

  const [showModalDespesa, setShowModalDespesa] = useState(false);
  const [modoEdicao, setModoEdicao] = useState(false);

  const [despesaData, setDespesaData] = useState({
    id: null,
    categoria: "",
    caminhao_id: "",
    descricao: "",
    observacoes: "",
    valor_total: "",
    tipo: "VARIAVEL",
    data_vencimento: "",
    data_pagamento: "",
    status: "PENDENTE",
    total_parcelas: 1,
  });

  const [showFiltro, setShowFiltro] = useState(false);
  const [filtro, setFiltro] = useState({
    categoria: "",
    caminhao: "",
    status: "",
    tipo: "",
    mes: "",
    ano: "",
  });

  // CARREGAR DADOS -------------------------------------------------------------
  useEffect(() => {
    carregarCategorias();
    carregarCaminhoes();
    carregarDespesas();
  }, []);

  const carregarCategorias = () => {
    api.get("/api/despesas/categorias/")
      .then((res) => {
        let data = [];
        if (Array.isArray(res.data)) {
          data = res.data;
        } else if (res.data.results) {
          data = res.data.results;
        }
        console.log("Categorias carregadas:", data);
        setCategorias(data);
        
        // Define primeira categoria como padrão
        if (data.length > 0) {
          setDespesaData(prev => ({
            ...prev,
            categoria: prev.categoria || data[0].id
          }));
        }
      })
      .catch((err) => console.error("Erro ao carregar categorias:", err));
  };

  const carregarCaminhoes = () => {
    api.get("/api/caminhoes/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || [];
        console.log("Caminhões carregados:", data);
        setCaminhoes(data);
      })
      .catch((err) => console.error("Erro ao carregar caminhões:", err));
  };

  const carregarDespesas = () => {
    api.get("/api/despesas/despesas/")
      .then((res) => {
        const data = Array.isArray(res.data) ? res.data : res.data.results || [];
        console.log("Despesas carregadas:", data);
        setDespesas(data);
        calcularTotais(data);
      })
      .catch((err) => console.error("Erro ao carregar despesas:", err));
  };

  // CALCULAR TOTAIS ------------------------------------------------------------
  const calcularTotais = (despesasList) => {
    const total = despesasList.reduce((acc, d) => acc + Number(d.valor_total || 0), 0);
    const pago = despesasList.filter(d => d.status === 'PAGO')
      .reduce((acc, d) => acc + Number(d.valor_total || 0), 0);
    const pendente = despesasList
      .filter(d => d.status === 'PENDENTE' || d.status === 'VENCIDO')
      .reduce((acc, d) => acc + Number(d.valor_total || 0), 0);

    setValorTotalGeral(total);
    setValorPago(pago);
    setValorPendente(pendente);
  };

  // HANDLERS DESPESA -----------------------------------------------------------
  const handleDespesaInputChange = (e) => {
  const { name, value } = e.target;

  setDespesaData((prev) => {
    
    let newValue = value;

    // Converte IDs numéricos
    if (name === "categoria" || name === "caminhao_id") {
      newValue = Number(value);
    }

    const newData = { ...prev, [name]: newValue };

    // Ajustes automáticos para tipo FIXA
    if (name === "tipo" && value !== "FIXA") {
      newData.total_parcelas = 1;
    }
    if (name === "tipo" && value === "FIXA" && prev.total_parcelas < 2) {
      newData.total_parcelas = 12;
    }

    return newData;
  });
};


  const handleAdicionarDespesa = () => {
    if (!despesaData.categoria || !despesaData.descricao || !despesaData.valor_total || !despesaData.data_vencimento) {
      alert("Preencha todos os campos obrigatórios!");
      return;
    }

    if (despesaData.tipo === "FIXA" && despesaData.total_parcelas < 2) {
      alert("Despesas do tipo FIXA devem ter pelo menos 2 parcelas!");
      return;
    }

    const payload = {
      categoria_id: Number(despesaData.categoria),
      caminhao_id: despesaData.caminhao_id ? Number(despesaData.caminhao_id) : null,
      descricao: despesaData.descricao,
      observacoes: despesaData.observacoes || "",
      valor_total: despesaData.valor_total,
      tipo: despesaData.tipo,
      data_vencimento: despesaData.data_vencimento,
      data_pagamento: despesaData.data_pagamento || null,
      status: despesaData.status,
      total_parcelas: Number(despesaData.total_parcelas) || 1,
    };

    if (modoEdicao && despesaData.id) {
      api.put(`/api/despesas/despesas/${despesaData.id}/`, payload)
        .then((res) => {
          fecharModalDespesa();
          carregarDespesas();
          alert("Despesa atualizada com sucesso!");
        })
        .catch((err) => {
          console.error("Erro ao editar:", err.response?.data);
          alert(err.response?.data?.detail || "Erro ao editar despesa.");
        });
    } else {
      api.post("/api/despesas/despesas/", payload)
        .then((res) => {
          fecharModalDespesa();
          carregarDespesas();
          if (despesaData.tipo === "FIXA") {
            alert(`✅ ${despesaData.total_parcelas} parcelas criadas com sucesso!`);
          } else {
            alert("✅ Despesa criada com sucesso!");
          }
        })
        .catch((err) => {
          console.error("Erro ao adicionar:", err.response?.data);
          alert("Erro ao adicionar despesa. Verifique o console.");
        });
    }
  };

  const handleEditarDespesa = (despesa) => {
    setModoEdicao(true);
    
    const categoriaId = typeof despesa.categoria === 'object' ? despesa.categoria?.id : despesa.categoria;
    const caminhaoId = typeof despesa.caminhao === 'object' ? despesa.caminhao?.id : despesa.caminhao;
    
    console.log("Editando despesa:", despesa);
    console.log("Categoria ID:", categoriaId);
    console.log("Caminhão ID:", caminhaoId);
    
    setDespesaData({
      id: despesa.id,
      categoria: categoriaId ? Number(categoriaId) : "",
      caminhao_id: caminhaoId || "",
      descricao: despesa.descricao,
      observacoes: despesa.observacoes || "",
      valor_total: despesa.valor_total,
      tipo: despesa.tipo,
      data_vencimento: despesa.data_vencimento,
      data_pagamento: despesa.data_pagamento || "",
      status: despesa.status,
      total_parcelas: despesa.total_parcelas || 1,
    });
    setShowModalDespesa(true);
  };

  const handleMarcarComoPago = (despesa) => {
    const categoriaId = typeof despesa.categoria === 'object' ? despesa.categoria?.id : despesa.categoria;
    const caminhaoId = typeof despesa.caminhao === 'object' ? despesa.caminhao?.id : despesa.caminhao;
    
    const payload = {
      categoria_id: categoriaId,
      caminhao_id: caminhaoId || null,
      descricao: despesa.descricao,
      observacoes: despesa.observacoes || "",
      valor_total: despesa.valor_total,
      tipo: despesa.tipo,
      data_vencimento: despesa.data_vencimento,
      status: "PAGO",
      data_pagamento: new Date().toISOString().split("T")[0],
      total_parcelas: despesa.total_parcelas || 1,
    };

    api.put(`/api/despesas/despesas/${despesa.id}/`, payload)
      .then(() => {
        carregarDespesas();
        alert("✅ Despesa marcada como paga!");
      })
      .catch((err) => console.error("Erro ao marcar como pago:", err));
  };

  const handleRemoverDespesa = (despesa) => {
    if (!window.confirm(`Tem certeza que deseja remover a despesa "${despesa.descricao}"?`)) {
      return;
    }

    api.delete(`/api/despesas/despesas/${despesa.id}/`)
      .then(() => {
        carregarDespesas();
        alert("✅ Despesa removida com sucesso!");
      })
      .catch((err) => {
        console.error("Erro ao remover despesa:", err);
        alert("❌ Erro ao remover despesa.");
      });
  };

  // MODAIS --------------------------------------------------------------------
  const abrirModalNovo = () => {
    setModoEdicao(false);
    setDespesaData({
      id: null,
      categoria: categorias.length > 0 ? Number(categorias[0].id) : "",
      caminhao_id: "",
      descricao: "",
      observacoes: "",
      valor_total: "",
      tipo: "VARIAVEL",
      data_vencimento: "",
      data_pagamento: "",
      status: "PENDENTE",
      total_parcelas: 1,
    });
    setShowModalDespesa(true);
  };

  const fecharModalDespesa = () => {
    setShowModalDespesa(false);
    setModoEdicao(false);
  };

  const aplicarFiltro = () => setShowFiltro(false);
  
  const limparFiltros = () => {
    setFiltro({
      categoria: "",
      caminhao: "",
      status: "",
      tipo: "",
      mes: "",
      ano: "",
    });
  };

  // FILTROS -------------------------------------------------------------------
  const despesasFiltradas = despesas.filter((d) => {
    if (filtro.categoria && d.categoria?.nome !== filtro.categoria) return false;
    if (filtro.caminhao && d.caminhao?.id != filtro.caminhao) return false;
    if (filtro.status && d.status !== filtro.status) return false;
    if (filtro.tipo && d.tipo !== filtro.tipo) return false;
    if (filtro.mes && new Date(d.data_vencimento).getMonth() + 1 != filtro.mes) return false;
    if (filtro.ano && new Date(d.data_vencimento).getFullYear() != filtro.ano) return false;
    return true;
  });

  const temFiltroAtivo =
    filtro.categoria || filtro.caminhao || filtro.status || filtro.tipo || filtro.mes || filtro.ano;

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case "PAGO": return "status-pago";
      case "PENDENTE": return "status-pendente";
      case "VENCIDO": return "status-vencido";
      case "CANCELADO": return "status-cancelado";
      default: return "status-pendente";
    }
  };

  const getTipoBadgeClass = (tipo) => {
    switch (tipo) {
      case "FIXA": return "tipo-fixa";
      case "VARIAVEL": return "tipo-variavel";
      case "RECORRENTE": return "tipo-recorrente";
      default: return "tipo-variavel";
    }
  };

  // Funções auxiliares
  const getNomeCategoria = (categoria) => {
    if (!categoria) return "—";
    if (typeof categoria === 'object') {
      return categoria.nome_display || categoria.nome || "—";
    }
    // Se for apenas ID, busca o nome
    const cat = categorias.find(c => c.id === categoria);
    return cat?.nome_display || cat?.nome || "—";
  };

  const getApelidoCaminhao = (caminhao) => {
    if (!caminhao) return "—";
    if (typeof caminhao === 'object') {
      return caminhao.apelido || caminhao.placa_cavalo || caminhao.nome_conjunto || "—";
    }
    // Se for apenas ID, busca o apelido
    const cam = caminhoes.find(c => c.id === caminhao);
    return cam?.apelido || cam?.placa_cavalo || cam?.nome_conjunto || "—";
  };

  const valorParcela = despesaData.tipo === "FIXA" && despesaData.valor_total && despesaData.total_parcelas > 0
    ? (Number(despesaData.valor_total) / Number(despesaData.total_parcelas)).toFixed(2)
    : "0.00";

  const valorTotalFiltrado = despesasFiltradas.reduce((acc, d) => acc + Number(d.valor_total || 0), 0);

  return (
  <div className="despesas-container">

    <h1 className="titulo">DESPESAS</h1>

    {/* BOTÕES */}
    <div className="btn-row">
      <button className="white-btn" onClick={abrirModalNovo}>
        NOVA DESPESA
      </button>

      <button className="white-btn" onClick={() => setShowFiltro(true)}>
        FILTRAR
      </button>
    </div>

    {/* INFO CARDS */}
    <div className="info-viagens">
      <p className="total-text">
        TOTAL DE DESPESAS: {despesasFiltradas.length}
      </p>
      <p className="total-valor">
        VALOR TOTAL: R$ {valorTotalFiltrado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
      </p>
    </div>

    {/* INDICADOR DE FILTROS ATIVOS */}
    {temFiltroAtivo && (
      <div className="filtros-aplicados">
        {filtro.categoria && <span className="filtro-badge">Categoria: {filtro.categoria}</span>}
        {filtro.caminhao && <span className="filtro-badge">Caminhão: {getApelidoCaminhao(caminhoes.find(c => c.id == filtro.caminhao))}</span>}
        {filtro.status && <span className="filtro-badge">Status: {filtro.status}</span>}
        {filtro.tipo && <span className="filtro-badge">Tipo: {filtro.tipo}</span>}
        {filtro.mes && <span className="filtro-badge">Mês: {filtro.mes}</span>}
        {filtro.ano && <span className="filtro-badge">Ano: {filtro.ano}</span>}
        <button className="filtro-badge filtro-limpar" onClick={limparFiltros}>✕ Limpar</button>
      </div>
    )}

    {/* TABELA */}
    <div className="table-wrapper">
      <table className="viagens-table">
        <thead>
          <tr>
            <th>DATA</th>
            <th>CATEGORIA</th>
            <th>CAMINHÃO</th>
            <th>DESCRIÇÃO</th>
            <th>VALOR</th>
            <th>TIPO</th>
            <th>STATUS</th>
            <th>AÇÕES</th>
          </tr>
        </thead>

        <tbody>
          {despesasFiltradas.length === 0 ? (
            <tr>
              <td colSpan="8" style={{ textAlign: "center", padding: 20 }}>
                Nenhuma despesa encontrada.
              </td>
            </tr>
          ) : (
            despesasFiltradas.map((d) => (
              <tr key={d.id}>
                <td>{new Date(d.data_vencimento).toLocaleDateString('pt-BR')}</td>
                
                <td>
                  <span className="categoria-badge">{getNomeCategoria(d.categoria)}</span>
                </td>

                <td>{getApelidoCaminhao(d.caminhao)}</td>

                <td>{d.descricao}</td>

                <td>R$ {Number(d.valor_total).toFixed(2)}</td>

                <td>
                  <span className={`status-badge ${getTipoBadgeClass(d.tipo)}`}>
                    {d.tipo}
                  </span>
                </td>

                <td>
                  <span className={`status-badge ${getStatusBadgeClass(d.status)}`}>
                    {d.status}
                  </span>
                </td>

                <td>
                  <div className="acoes-row">
                    <button
                      className="btn-editar"
                      onClick={() => handleEditarDespesa(d)}
                    >
                      EDITAR
                    </button>

                    {d.status !== "PAGO" && (
                      <button
                        className="btn-pagar"
                        onClick={() => handleMarcarComoPago(d)}
                      >
                        PAGAR
                      </button>
                    )}

                    <button
                      className="btn-remover"
                      onClick={() => handleRemoverDespesa(d)}
                    >
                      REMOVER
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>

    {/* MODAL CADASTRO/EDIÇÃO */}
    {showModalDespesa && (
      <div className="modal-overlay" onClick={fecharModalDespesa}>
        <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
          <h2>{modoEdicao ? "Editar Despesa" : "Nova Despesa"}</h2>

          {/* Categoria */}
          <div className="form-group">
            <label>Categoria*</label>
            <select
              name="categoria"
              value={despesaData.categoria}
              onChange={handleDespesaInputChange}
            >
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome_display || c.nome}
                </option>
              ))}
            </select>
          </div>

          {/* Caminhão */}
          <div className="form-group">
            <label>Caminhão</label>
            <select
              name="caminhao_id"
              value={despesaData.caminhao_id}
              onChange={handleDespesaInputChange}
            >
              <option value="">Nenhum</option>
              {caminhoes.map((cam) => (
                <option key={cam.id} value={cam.id}>
                  { cam.nome_conjunto }
                </option>
              ))}
            </select>
          </div>

          {/* Descrição */}
          <div className="form-group">
            <label>Descrição*</label>
            <input
              type="text"
              name="descricao"
              value={despesaData.descricao}
              onChange={handleDespesaInputChange}
            />
          </div>

          {/* Observações */}
          <div className="form-group">
            <label>Observações</label>
            <input
              type="text"
              name="descricao"
              value={despesaData.descricao}
              onChange={handleDespesaInputChange}
            />
          </div>

          {/* Valor */}
          <div className="form-group">
            <label>Valor Total*</label>
            <input
              type="number"
              name="valor_total"
              value={despesaData.valor_total}
              onChange={handleDespesaInputChange}
            />
          </div>

          {/* Tipo */}
          <div className="form-group">
            <label>Tipo</label>
            <select
              name="tipo"
              value={despesaData.tipo}
              onChange={handleDespesaInputChange}
            >
              <option value="VARIAVEL">Variável</option>
              <option value="FIXA">Fixa</option>
              <option value="RECORRENTE">Recorrente</option>
            </select>
          </div>

          {/* Parcelas */}
          {despesaData.tipo === "FIXA" && (
            <>
              <div className="form-group">
                <label>Total de Parcelas</label>
                <input
                  type="number"
                  name="total_parcelas"
                  min="2"
                  value={despesaData.total_parcelas}
                  onChange={handleDespesaInputChange}
                />
              </div>

              <p className="parcela-info">
                Valor por parcela: <strong>R$ {valorParcela}</strong>
              </p>
            </>
          )}

          {/* Datas */}
          <div className="form-group">
            <label>Vencimento*</label>
            <input
              type="date"
              name="data_vencimento"
              value={despesaData.data_vencimento}
              onChange={handleDespesaInputChange}
            />
          </div>

          <div className="form-group">
            <label>Data de Pagamento</label>
            <input
              type="date"
              name="data_pagamento"
              value={despesaData.data_pagamento}
              onChange={handleDespesaInputChange}
            />
          </div>

          {/* Status */}
          <div className="form-group">
            <label>Status</label>
            <select
              name="status"
              value={despesaData.status}
              onChange={handleDespesaInputChange}
            >
              <option value="PENDENTE">Pendente</option>
              <option value="PAGO">Pago</option>
              <option value="VENCIDO">Vencido</option>
              <option value="CANCELADO">Cancelado</option>
            </select>
          </div>

          {/* Botões */}
          <div className="modal-buttons">
            <button className="btn-salvar" onClick={handleAdicionarDespesa}>
              {modoEdicao ? "SALVAR" : "ADICIONAR"}
            </button>

            <button className="btn-cancelar" onClick={fecharModalDespesa}>
              CANCELAR
            </button>
          </div>
        </div>
      </div>
    )}

    {/* MODAL DE FILTRO */}
    {showFiltro && (
      <div className="modal-overlay" onClick={() => setShowFiltro(false)}>
        <div className="modal-edicao" onClick={(e) => e.stopPropagation()}>
          <h2>Filtrar Despesas</h2>

          <div className="form-group">
            <label>Categoria</label>
            <select
              value={filtro.categoria}
              onChange={(e) =>
                setFiltro({ ...filtro, categoria: e.target.value })
              }
            >
              <option value="">Todas</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.nome}>
                  {c.nome_display || c.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Caminhão</label>
            <select
              value={filtro.caminhao}
              onChange={(e) =>
                setFiltro({ ...filtro, caminhao: e.target.value })
              }
            >
              <option value="">Todos</option>
              {caminhoes.map((cam) => (
                <option key={cam.id} value={cam.id}>
                  {cam.nome_conjunto}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Status</label>
            <select
              value={filtro.status}
              onChange={(e) =>
                setFiltro({ ...filtro, status: e.target.value })
              }
            >
              <option value="">Todos</option>
              <option value="PAGO">Pago</option>
              <option value="PENDENTE">Pendente</option>
              <option value="VENCIDO">Vencido</option>
              <option value="CANCELADO">Cancelado</option>
            </select>
          </div>

          <div className="form-group">
            <label>Tipo</label>
            <select
              value={filtro.tipo}
              onChange={(e) =>
                setFiltro({ ...filtro, tipo: e.target.value })
              }
            >
              <option value="">Todos</option>
              <option value="VARIAVEL">Variável</option>
              <option value="FIXA">Fixa</option>
              <option value="RECORRENTE">Recorrente</option>
            </select>
          </div>

          <div className="form-group">
            <label>Mês</label>
            <input
              type="number"
              min="1"
              max="12"
              value={filtro.mes}
              onChange={(e) =>
                setFiltro({ ...filtro, mes: e.target.value })
              }
            />
          </div>

          <div className="form-group">
            <label>Ano</label>
            <input
              type="number"
              value={filtro.ano}
              onChange={(e) =>
                setFiltro({ ...filtro, ano: e.target.value })
              }
            />
          </div>

          <div className="modal-buttons">
            <button className="btn-salvar" onClick={aplicarFiltro}>
              APLICAR
            </button>

            <button className="btn-cancelar" onClick={() => setShowFiltro(false)}>
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